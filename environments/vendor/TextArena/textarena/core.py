import random
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Dict, List, Tuple, Optional, Callable
import inspect, functools

from textarena.utils.locales import LocalizedMessage, build_locale

class ObservationType(Enum):
    PROMPT = auto()                     
    PLAYER_ACTION = auto()                                 
    GAME_ACTION_DESCRIPTION = auto()                                      
    GAME_MESSAGE = auto()                                                        
    GAME_BOARD = auto()                                      
    GAME_ADMIN = auto()                                


GAME_ID = -1                                    
Message = Tuple[int, str, ObservationType]                        
Observations = dict[int, List[Message]]                                                                
Rewards = Dict[int, int]                            
Info = Dict[str, Any]                                                


class State:
    lang = "en"
    def __init__(self, num_players: int, seed: Optional[int]=None, max_turns: Optional[int]=None):
        if seed is not None: random.seed(seed)                      
        self.max_turns = max_turns 
        self.num_players = num_players
        self.current_player_id = 0

    def t(self, *keys, _pid: int = None, **kwargs) -> str:
        assert self._locale is not None, f"{self.__class__.__name__} has no locales/ folder."
        return self._locale.t(*keys, _pid=_pid, **kwargs)
    
    def m(self, *keys, **kwargs):
        return LocalizedMessage(key=keys, kwargs=kwargs, loader=self._locale)

    def check_turn_limit(self):
        return self.turn >= self.max_turns and self.done == False

    def update_current_player_id(self, player_id: int):
        assert player_id in self.role_mapping, f"Tried to update current player to {player_id}, which does not exist. Available players: {list(self.role_mapping.keys())}"

    def standard_resets(self, game_state: Optional[Dict[str, Any]]=None, player_prompt_function: Optional[Callable]=None, role_mapping: Optional[Dict[int, str]]={}, secret_roles: Optional[Dict[int, str]]=None):
        self.game_state = game_state
        self._locale = build_locale(lang=self.lang)
        
                                        
        self.turn = 0
        self.done = False 
        self.step_info = {}                                 
        self.game_info = {pid: {"role": self.t("PlayerRoleMapping", "player", player_id=pid, _pid=pid), "invalid_move": False, "turn_count": 0} for pid in range(self.num_players)}                                  
                                                                                                                                                                                       
                                                                                                                                   
                                                                                                                           
        if secret_roles is not None:
            for pid, role in secret_roles.items():
                self.game_info[pid]["role"] = role                                                       
                
        self.observations = {pid: [] for pid in range(self.num_players)}
        self.rewards = None
        self.logs = []

                          
        self.role_mapping = role_mapping
        if self.role_mapping is None:
            self.role_mapping = {pid: self.t("PlayerRoleMapping", "player", player_id=pid, _pid=pid) for pid in range(self.num_players)}
        self.role_mapping[GAME_ID] = self.role_mapping.get(GAME_ID, "GAME")                      

                                     
        if player_prompt_function is not None:
            for player_id in range(self.num_players):
                self.add_observation(to_id=player_id, message=player_prompt_function(player_id=player_id, game_state=self.game_state), observation_type=ObservationType.PROMPT)

    def add_observation(self, message, observation_type: ObservationType,
                        from_id: int = GAME_ID, to_id: int = -1):
        recipients = range(self.num_players) if to_id == -1 else [to_id]
        if to_id != -1:
            assert to_id in self.observations, (
                f"The provided 'to_id' {to_id} does not exist. "
                f"({list(self.observations.keys())})"
            )

        for pid in recipients:
            rendered = self._resolve_message(message, recipient_id=pid,
                                            from_id=from_id,
                                            observation_type=observation_type)
            if observation_type == ObservationType.PLAYER_ACTION:
                for role_tag in self.role_mapping.values():
                    rendered = rendered.replace(f"[{role_tag}]", "")
            self.observations[pid].append((from_id, rendered, observation_type))

                                                                              
                                                                                 
        log_text = self._resolve_message(
            message,
            recipient_id=from_id if observation_type == ObservationType.PLAYER_ACTION else None,
            from_id=from_id,
            observation_type=observation_type,
        )
        if observation_type == ObservationType.PLAYER_ACTION:
            for role_tag in self.role_mapping.values():
                log_text = log_text.replace(f"[{role_tag}]", "")
        self.logs.append((from_id, log_text))


                                  
    def _resolve_message(self, message, recipient_id, from_id, observation_type) -> str:
        from textarena.utils.locales import LocalizedMessage
        if not isinstance(message, LocalizedMessage):
            return message
        pid_for_lang = from_id if observation_type == ObservationType.PLAYER_ACTION else recipient_id
        return message.render(_pid=pid_for_lang)                                

    def get_current_player_observation(self):
        current_player_observation = self.observations[self.current_player_id]
        self.observations[self.current_player_id] = []
        return current_player_observation

    def step(self):
        if self.done: return (True, self.step_info)                                                   
        self.turn += 1                         
        step_info = self.step_info 
        self.step_info = {}             
        return (self.done, step_info)

    def close(self):
        return self.rewards, self.game_info


class Env(ABC):
    pass                                                         

                                                                            
                                                                                 
                                                                        
       
    allow_common_locale_fallback = False
    game_state: State

    lang = "en"
    _locale = None

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        original_reset = cls.__dict__.get("reset", None)
        if original_reset is None:
            return
        
        parameters = inspect.signature(original_reset).parameters
        lang_mapping_in_reset = "lang_mapping" in parameters

        @functools.wraps(original_reset)
        def reset_with_lang_mapping(self, num_players, seed=None, lang_mapping=None, *args, **kwargs):
            assert len(lang_mapping) == num_players if lang_mapping is not None else True, (f"Length of lang_mapping ({len(lang_mapping)}) does not match num_players ({num_players}).")
            if lang_mapping is None:
                lang_mapping = {pid: self.lang for pid in range(num_players)}
            self.set_lang(lang_mapping)
            if lang_mapping_in_reset:
                kwargs.setdefault("lang_mapping", lang_mapping)
            return original_reset(self, num_players, seed=seed, *args, **kwargs)
        
        cls.reset = reset_with_lang_mapping
    
    def set_lang(self, lang):
        self.lang = lang
        self._locale = build_locale(self.__class__, lang=lang)

        if (self._locale is None and self.allow_common_locale_fallback):
            self._locale = build_locale(lang=lang)

        all_en = (
            lang == "en"
            or (
                isinstance(lang, dict)
                and all(value == "en" for value in lang.values())
            )
        )

        if self._locale is None and not all_en:
            raise FileNotFoundError(
                f"{self.__class__.__name__} does not support lang='{lang}'. "
                f"Please add a locales/ folder with a '<lang>.json' file."
            )
        
        State.lang = lang
        Agent.lang = lang

    def t(self, *keys: str, _pid: int = None, **kwargs: Any) -> str:
        if self._locale is None:
            raise ValueError(f"Environment {self.__class__.__name__} has no locale data. Cannot call t() for translation. Please ensure there is a locales/ directory with the appropriate language files, or set lang='en' to use the default (which is just the keys).")
        return self._locale.t(*keys, _pid=_pid, **kwargs)
    
    def m(self, *keys, **kwargs):
        return LocalizedMessage(key=keys, kwargs=kwargs, loader=self._locale)

    @abstractmethod
    def reset(self, num_players: int, seed: Optional[int]=None):
        pass                                                   

             
                                                             
                                                                                                 
           
        raise NotImplementedError

    @abstractmethod
    def step(self, action: str) -> Tuple[bool, Info]:
        pass                                                  

             
                                                                    
                                                               

                
                             
                                                                
                                                                                      
           
        raise NotImplementedError

    def get_observation(self):
        return self.state.current_player_id, self.state.get_current_player_observation()

    def close(self):
        rewards = self.state.close()
        return rewards


class Wrapper(Env):
    pass                                        
    allow_common_locale_fallback = True
    
    def __init__(self, env):
                                                                       
        if isinstance(env, Wrapper) and env.is_wrapped_with(type(self)):
            raise ValueError(f"Environment is already wrapped with {type(self).__name__}. Double-wrapping is not allowed.")
        self.env = env

    def t(self, *keys, _pid: int = None, **kwargs) -> str:
        assert self._locale is not None, f"{self.__class__.__name__} has no locales/ folder."
        return self._locale.t(*keys, _pid=_pid, **kwargs)
    
    def m(self, *keys, **kwargs):
        return LocalizedMessage(key=keys, kwargs=kwargs, loader=self._locale)

    def __getattr__(self, name):
        return getattr(self.env, name)

    def reset(self, num_players: int , seed: Optional[int] = None, lang_mapping: Optional[Dict[int, str]] = None):
        self.lang = lang_mapping
        self._locale = build_locale(lang=self.lang)
        return self.env.reset(num_players=num_players, seed=seed, lang_mapping=lang_mapping)

    def step(self, action: str) -> Tuple[bool, Info]:
        return self.env.step(action=action)

    def get_observation(self):
        return self.env.get_observation()

    def close(self):
        return self.env.close()

    def __deepcopy__(self, memo):
        import copy
        copied_env = copy.deepcopy(self.env, memo)                                   
        cls = self.__class__                                        
        copied_wrapper = cls(copied_env)
        for k, v in self.__dict__.items():                                             
            if k != "env":
                setattr(copied_wrapper, k, copy.deepcopy(v, memo))
        return copied_wrapper

    def is_wrapped_with(self, wrapper_class: type) -> bool:
        env = self
        while isinstance(env, Wrapper):
            if isinstance(env, wrapper_class):
                return True
            env = env.env
        return False


class ObservationWrapper(Wrapper):
    def get_observation(self):
        player_id, observation = self.env.get_observation()
        return player_id, self.observation(player_id, observation)
    
    def observation(self):
        raise NotImplementedError


class RenderWrapper(Wrapper):
    def step(self, action: str) -> Tuple[bool, Optional[Info]]:
        return self.env.step(action=action)
    
    def reset(self, num_players: int , seed: Optional[int] = None, lang_mapping: Optional[Dict[int, str]] = None):
        self.reset_render()
        return self.env.reset(num_players=num_players, seed=seed, lang_mapping=lang_mapping)

    def reset_render(self):
        raise NotImplementedError


class ActionWrapper(Wrapper):
    def step(self, action: str) -> Tuple[bool, Optional[Info]]:
        return self.env.step(action=self.action(action))

    def action(self, action: str) -> str:
        raise NotImplementedError


class Agent(ABC):
    lang = "en"
    def __init__(self):
        self._locale = None
        self._loaded_lang = None

    def t(self, *keys, **kwargs) -> str:
        pass                                                        
        current_lang = self.__class__.lang
        if self._locale is None or self._loaded_lang != current_lang:
            self._locale = build_locale(lang=current_lang)
            self._loaded_lang = current_lang
        assert self._locale is not None, f"{self.__class__.__name__} has no locales/ folder."
        return self._locale.t(*keys, **kwargs)

    @abstractmethod
    def __call__(self, observation: str) -> str:
        pass                                                      

             
                                                           

                
                                                     
           
        pass


class AgentWrapper(Agent):
    pass        
    def __init__(self, agent: Agent):
        pass        
        self.agent = agent 
        assert isinstance(agent, Agent)

    def __getattr__(self, name):
        pass        
        return getattr(self.agent, name)

    def __call__(self, observation: str) -> str:
        return self.agent(observation=observation)




