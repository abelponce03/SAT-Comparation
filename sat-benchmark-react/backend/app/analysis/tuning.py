import os
import asyncio
from typing import List, Dict, Any, Optional

import numpy as np
from ConfigSpace import Configuration, ConfigurationSpace, Float, Integer, Categorical
from smac import Scenario
from smac.facade.algorithm_configuration_facade import AlgorithmConfigurationFacade
from smac.runhistory.dataclasses import TrialValue, TrialInfo

from app.solvers.registry import solver_registry

class TunableSolverBase:
    """
    Clase base para la definición de los Configuration Spaces (ConfigSpaces)
    para cada solver específico. Aquí se declaran los parámetros sintonizables.
    """
    
    @staticmethod
    def get_config_space() -> ConfigurationSpace:
        raise NotImplementedError("Debe ser implementado por la clase concreta.")


class KissatTunable(TunableSolverBase):
    @staticmethod
    def get_config_space() -> ConfigurationSpace:
        cs = ConfigurationSpace()
        
        # Parámetros comunes de Kissat basados en heurísticas de reinicio y garbage collection
        # Ejemplos ficticios/comunes, ajustar contra los manuales de Kissat
        restart_int = Integer("restartint", bounds=(100, 10000), default=1000)
        reduce_init = Integer("reduceinit", bounds=(100, 10000), default=300)
        phase_saving = Categorical("phasesaving", choices=[0, 1, 2], default=1)
        tier2 = Integer("tier2", bounds=(1, 100), default=3)
        promoted = Integer("promoted", bounds=(0, 10), default=1)
        walkinitially = Categorical("walkinitially", choices=[0, 1], default=0)
        
        cs.add_hyperparameters([restart_int, reduce_init, phase_saving, tier2, promoted, walkinitially])
        return cs


class CaDiCaLTunable(TunableSolverBase):
    @staticmethod
    def get_config_space() -> ConfigurationSpace:
        cs = ConfigurationSpace()
        
        # Parámetros de CaDiCaL
        restart = Categorical("restart", choices=[0, 1], default=1) # 1: activo, 0: inactivo
        restartint = Integer("restartint", bounds=(1, 10000), default=2)
        elim = Categorical("elim", choices=[0, 1], default=1)
        subsume = Categorical("subsume", choices=[0, 1], default=1)
        
        cs.add_hyperparameters([restart, restartint, elim, subsume])
        return cs


class AlgorithmTuner:
    """
    Motor central de integración SMAC3 para el Tuning de los SAT solvers.
    Permite el fitting de los hiperparámetros contra un set de instancias SAT.
    Incorpora penalizaciones masivas a los falsos UNSAT, SEGFAULTS o timeouts 
    acercándose así tempranamente al Bug-finding y validando la robustez.
    """
    
    def __init__(self, solver_name: str, instances: List[str], timeout_per_run: float = 300.0, max_evaluations: int = 100):
        self.solver_name = solver_name
        self.instances = instances
        self.timeout_per_run = timeout_per_run
        self.max_evaluations = max_evaluations
        
        self.config_spaces = {
            "kissat": KissatTunable,
            "cadical": CaDiCaLTunable,
            # Añadir más mappings en el futuro
        }
    
    def get_solver_config_space(self) -> ConfigurationSpace:
        tuner_class = self.config_spaces.get(self.solver_name.lower())
        if not tuner_class:
            raise ValueError(f"No ConfigSpace definido para: {self.solver_name}")
        return tuner_class.get_config_space()

    def _format_config_to_args(self, config: Configuration) -> List[str]:
        """
        Convierte el objeto Configuration dict-like a la sintaxis del SAT solver.
        Por ejemplo: --restart=0 --restartint=22
        """
        args = []
        for key, value in config.items():
            args.append(f"--{key}={value}")
        return args

    def evaluate_runner(self, config: Configuration, instance: str, seed: int = 0) -> float:
        """
        La Función Objetivo sincrónica utilizada por SMAC3.
        Mide el PAR-2 score para la configuración dada en la instancia proporcionada.
        También implementa el Bug-finding penalizando drásticamente fallos catastróficos.
        """
        # Obtenemos la instancia del solver plugin (ej: GenericSolverPlugin configurado para Kissat)
        # Nota: El event loop acá es complicado porque SMAC3 usa funciones síncronas para evaluar.
        # Corremos el wrapper asyncónico a través de asyncio.run
        
        return asyncio.run(self._async_evaluate(config, instance, timeout_per_run=self.timeout_per_run))

    async def _async_evaluate(self, config: Configuration, instance: str, timeout_per_run: float) -> float:
        try:
            plugin = solver_registry.get_by_key(self.solver_name.lower())
            
            # Formateando argumentos desde ConfigSpace a la línea de comandos
            custom_args = self._format_config_to_args(config)
            
            # plugin.run() es async y devuelve un SolverRunResult
            result = await plugin.run(instance_path=instance, timeout=int(timeout_per_run), extra_args=custom_args)
            
            # --- EVALUACIÓN PAR-2 SCORE Y BUG FOUND ---
            
            if result.status == "ERROR" or result.return_code not in [10, 20, 0]:
                # SEGFAULT / CRASH / BUG -> Penalización extrema (Bug-finding model [ELH19])
                print(f"[BUG-FINDING] Crash detected on instance {instance} with config {config.get_dictionary()}")
                return timeout_per_run * 10000.0  # Penalización titánica
            
            elif result.status == "TIMEOUT":
                # PAR-2 Factorización
                return timeout_per_run * 2.0
            
            elif result.status in ["SAT", "UNSAT"]:
                # Retornamos el tiempo real incurrido. Podemos usar result.real_time_seconds 
                # (o user_time_seconds, dependiendo del metric objetivo preferido)
                return result.real_time_seconds if result.real_time_seconds is not None else float(result.execution_time)
            
            else:
                return timeout_per_run * 2.0 # Fallback
                
        except Exception as e:
            # Fatal python error, also penalize
            return timeout_per_run * 10000.0


    def run_tuning(self):
        """
        Ejecuta el ciclo de optimización secuencial de hiperparámetros utilizando SMAC.
        """
        cs = self.get_solver_config_space()

        # Configuración del escenario ("Scenario")
        scenario = Scenario(
            configspace=cs,
            deterministic=True,  # SAT solvers asumen determinismo salvo se fije seed
            instances=self.instances,
            walltime_limit=self.timeout_per_run * self.max_evaluations, # Límite max global de pared
            n_trials=self.max_evaluations, 
        )

        print(f"--- Iniciando Tuning para {self.solver_name.upper()} ---")
        print(f"Espacio de Configuración: {cs}")

        # Configurar Facade principal de SMAC
        smac = AlgorithmConfigurationFacade(
            scenario=scenario,
            target_function=self.evaluate_runner,
            overwrite=True
        )

        incumbent = smac.optimize()

        print("--- Tuning Finalizado ---")
        print(f"Mejor configuración (Incumbent): {incumbent}")
        
        # Retorna el mejor candidato para guardarlo o utilizarlo (Ablation Analysis futuro)
        return incumbent
