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

class AblationAnalyzer:
    """
    Sub-módulo para ejecutar Análisis de Ablación post-Tuning [FH16].
    Compara 1 a 1 los parámetros que fueron modificados con respecto al default,
    determinando el beneficio (peso estadístico/mejora de PAR-2) asociado a cada hiperparámetro.
    """
    
    def __init__(self, solver_name: str, instances: List[str], timeout_per_run: float = 300.0):
        self.solver_name = solver_name
        self.instances = instances
        self.timeout_per_run = timeout_per_run
        self.tuner = AlgorithmTuner(solver_name, instances, timeout_per_run)

    def _get_default_config(self) -> Configuration:
        return self.tuner.get_solver_config_space().get_default_configuration()

    async def _evaluate_single_config(self, config: Configuration) -> float:
        """ Evalúa el PAR-2 score de una configuración específica promediando sus instancias """
        total_par2 = 0.0
        # Promedio sobre las instancias de test
        for instance in self.instances:
            score = await self.tuner._async_evaluate(config, instance, self.timeout_per_run)
            total_par2 += score
        return total_par2 / max(1, len(self.instances))

    async def analyze_ablation(self, incumbent_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta the ablation sequence (simplificada) from Default to Incumbent
        """
        cs = self.tuner.get_solver_config_space()
        default_config = cs.get_default_configuration()
        
        incumbent_config = Configuration(cs, values=incumbent_dict)
        
        # 1. Base scores
        default_score = await self._evaluate_single_config(default_config)
        incumbent_score = await self._evaluate_single_config(incumbent_config)
        
        print(f"[Ablation] Default PAR-2: {default_score} | Incumbent PAR-2: {incumbent_score}")
        
        # 2. Encontramos parámetros que cambiaron
        flipped_params = {}
        for param in cs.get_hyperparameter_names():
            def_val = default_config.get(param)
            inc_val = incumbent_config.get(param)
            if def_val != inc_val:
                flipped_params[param] = {"default": def_val, "incumbent": inc_val}
                
        # 3. Flips 1-a-1 evaluando el impacto
        # Calculamos cuál es la mejora si a la confiuguración default le ponemos SOLO ESE parámetro del incumbent
        ablation_results = {}
        total_improvement = default_score - incumbent_score
        
        for param, values in flipped_params.items():
            test_dict = default_config.get_dictionary().copy()
            test_dict[param] = values["incumbent"]
            
            test_config = Configuration(cs, values=test_dict)
            test_score = await self._evaluate_single_config(test_config)
            
            improvement = default_score - test_score
            ablation_results[param] = {
                "default_value": values["default"],
                "incumbent_value": values["incumbent"],
                "par2_score": test_score,
                "improvement": improvement,
                "percentage_of_total_gain": (improvement / total_improvement * 100) if total_improvement > 0 else 0
            }
            
        # Sort de mayor a menor impacto
        sorted_ablation = dict(sorted(ablation_results.items(), key=lambda item: item[1]['improvement'], reverse=True))
        
        return {
            "baseline_default_score": default_score,
            "incumbent_score": incumbent_score,
            "total_improvement": total_improvement,
            "parameters_impact": sorted_ablation
        }
