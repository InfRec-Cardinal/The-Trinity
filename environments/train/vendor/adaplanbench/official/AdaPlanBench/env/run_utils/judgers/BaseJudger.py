from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from ..llm import ModelConfig


class BaseJudger(ABC):
    @abstractmethod
    def judge_env_constraints_one_model(
        self,
        *,
        query: str,
        plan: str,
        banned_tools: str,
        judge_model: ModelConfig,
    ) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def judge_user_prefs_one_model(
        self,
        *,
        query: str,
        plan: str,
        user_prefs: str,
        judge_model: ModelConfig,
    ) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def judge_rubrics_one_model(
        self,
        *,
        query: str,
        plan: str,
        judge_model: ModelConfig,
    ) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def generate_user_feedback(
        self,
        *,
        query: str,
        plan: str,
        judge_feedback: str,
        memory: str,
        refine_rubrics: str,
        tools_placeholder: str,
        prefs_placeholder: str,
    ) -> str:
        raise NotImplementedError
