import json, logging
import ssl
import asyncio
from typing import List, Optional, Tuple, Dict, Any, Union
from urllib.parse import urlencode
import warnings
from urllib3.exceptions import InsecureRequestWarning
import uuid
from textarena.envs.registration import ENV_REGISTRY


                              
try:
    import requests, websockets
except ImportError:
    raise ImportError("'requests' and 'websockets' libraries are required for online play. Install them with: 'pip install textarena[online]' OR pip install requests, websockets'")


                       
warnings.filterwarnings('ignore', category=InsecureRequestWarning)

                                                 
MATCHMAKING_WS_URI = "wss://matchmaking.textarena.ai/ws"
MATCHMAKING_HTTP_URI = "https://matchmaking.textarena.ai"

                        
NAME_TO_ID_DICT = { 
    "Chess-v0": 0,
    "DontSayIt-v0": 3,
    "LiarsDice-v0": 6,
    "SimpleNegotiation-v0": 8,
    "SpellingBee-v0": 10,
    "TicTacToe-v0": 35,
    "Othello-v0": 51,
    "PigDice-v0": 52,
    "Poker-v0": 68,
    "Snake-v0-standard": 70,
    "SecretMafia-v0": 75,
    "SimpleTak-v0": 84,
}

def strip_env_variant(env_id: str) -> str:
    for suffix in ["-train", "-raw"]:
        if env_id.endswith(suffix):
            return env_id[: -len(suffix)]
    return env_id

class DynamicWrapperProxy:
    pass                                                                          
    
    def __init__(self, base_env, env_id_to_wrappers_map):
        self.base_env = base_env
        self.env_id_to_wrappers_map = env_id_to_wrappers_map
        self.wrapped_env = None
        self.matched_env_id = None
        self._wrappers_applied = False
        
    def _apply_wrappers_for_env(self, env_id):
        pass                                                              
        if self._wrappers_applied:
            return                   
            
        self.matched_env_id = env_id
        
                                                
        wrappers = self.env_id_to_wrappers_map.get(env_id, [])
        
        if wrappers:
            self.wrapped_env = self.base_env
            for wrapper in wrappers:
                self.wrapped_env = wrapper(self.wrapped_env)
        else:
            self.wrapped_env = self.base_env
        
        self._wrappers_applied = True
    
    def _get_active_env(self):
        pass                                                         
        if not self._wrappers_applied and hasattr(self.base_env, 'matched_env_name') and self.base_env.matched_env_name:
            self._apply_wrappers_for_env(self.base_env.matched_env_name)
        
        return self.wrapped_env if self.wrapped_env is not None else self.base_env
    
    def get_observation(self):
        pass                                                                      
                                            
        if not self._wrappers_applied:
            if hasattr(self.base_env, 'matched_env_name') and self.base_env.matched_env_name:
                self._apply_wrappers_for_env(self.base_env.matched_env_name)
        
        active_env = self._get_active_env()
        return active_env.get_observation()
    
    def step(self, action):
        pass                                                           
        active_env = self._get_active_env()
        return active_env.step(action)
    
    def reset(self, *args, **kwargs):
        pass                                                            
                                          
        result = self.base_env.reset(*args, **kwargs)
        
                                                                       
        if hasattr(self.base_env, 'matched_env_name') and self.base_env.matched_env_name and not self._wrappers_applied:
            self._apply_wrappers_for_env(self.base_env.matched_env_name)
            
        return result
    
    def close(self):
        pass                             
        active_env = self._get_active_env()
        return active_env.close()
    
    def __getattr__(self, name):
        pass                                                                
        return getattr(self._get_active_env(), name)


class OnlineEnvWrapper:
    def __init__(self, env_ids: List[int], env_id_names: List[str], model_name: str, model_token: str):
        self.env_ids = env_ids
        self.env_id_names = env_id_names                                   
        self.model_name = model_name
        self.model_token = model_token
        
                              
        self.websocket = None
        self.matchmaking_websocket = None
        self.game_url = None
        self.environment_id = None
        self.env_id = None
        self.matched_env_name = None                                      
        
                                                      
        self.env_id_to_wrappers_map = {}
        for env_name in env_id_names:
            if env_name in ENV_REGISTRY:
                env_spec = ENV_REGISTRY[env_name]
                self.env_id_to_wrappers_map[env_name] = env_spec.default_wrappers or []
        
                                                                                                                   
        self.full_observations = {}
        
                             
        self.current_player_id = None
        self.current_observation = None
        self.game_over = False
        self.server_shutdown = False
        self.game_over_timeout = 30.0

        self.rewards = {}
        self.step_info = {}
        self.game_info = {}
        
                  
        self.matchmaking_timeout = 1800

        
                                                     
        self.message_queue = asyncio.Queue()
        self.action_queue = asyncio.Queue()
        self.matchmaking_queue = asyncio.Queue()
        
                        
        self.in_game = False
        self.pending_action = False
        self.update_task = None
        self.matchmaking_complete = False
        
                           
        DummyState = type("DummyState", (), {})
        self.state = DummyState()
        self.state.role_mapping = {0: "Player 0", 1: "Player 1", -1: "GAME"}

    async def _message_receiver(self):
        pass                                                                               
                                                                       
        
                                                                                            
           
        try:
            while True:
                try:
                    message = await self.websocket.recv()
                    print(f"Received: {message}")

                                                                       
                    await self.message_queue.put(message)
                    
                                                                                         
                    try:
                        msg_data = json.loads(message)
                        if msg_data.get("command") == "server_shutdown":
                            print("Server shutdown message detected in receiver")
                            self.server_shutdown = True
                    except:
                        pass
                        
                except websockets.exceptions.ConnectionClosed:
                    print("WebSocket connection closed by server")
                    self.server_shutdown = True
                    break

                except Exception as e:
                    print(f"Error receiving message: {e}")
                    break

        except Exception as e:
            print(f"Message receiver error: {e}")
            self.server_shutdown = True

    async def _matchmaking_receiver(self):
        pass                                                                  
        
                                                                                            
           
        try:
            while not self.matchmaking_complete:
                try:
                    message = await self.matchmaking_websocket.recv()
                    print(f"Received from matchmaking: {message}")

                                                                                  
                    await self.matchmaking_queue.put(message)

                except websockets.exceptions.ConnectionClosed:
                    print("Matchmaking WebSocket connection closed")
                    break

                except Exception as e:
                    print(f"Error receiving matchmaking message: {e}")
                    break

        except Exception as e:
            print(f"Matchmaking receiver error: {e}")

    async def _action_sender(self):
        pass                                                                                                         

                                                                                                                   
           
        try:
            while True:
                                                  
                action = await self.action_queue.get()

                                                         
                if action == "CLOSE":
                    break
                
                try:
                                                
                    action_msg = {"command": "action", "action": action}
                    await self.websocket.send(json.dumps(action_msg))
                    print(f"Sent action: {action[:100]}...")

                                                                                   
                    self.pending_action = True

                except Exception as e:
                    print(f"Error sending action: {e}")
                
                                                                                               
                self.action_queue.task_done()

        except Exception as e:
            print(f"Action sender error: {e}")
            self.server_shutdown = True


    async def _ping_sender(self):
        pass                                                                  

                                                                                             
           
        try:
            while not self.server_shutdown:
                try:
                                                       
                    await self.websocket.send(json.dumps({"command": "ping"}))
                    await asyncio.sleep(25)
                except Exception as e:
                    print(f"Ping error: {e}")
                    break

        except Exception as e:
            print(f"Ping sender error: {e}")
            self.server_shutdown = True


    def _get_env_name_from_id(self, env_id):
        pass                                                         
                                
        id_to_name = {v: k for k, v in NAME_TO_ID_DICT.items()}
        base_name = id_to_name.get(env_id)
        
        if base_name:
                                                                            
            for env_name in self.env_id_names:
                if strip_env_variant(env_name) == base_name:
                    return env_name
        
        return base_name

    async def _process_matchmaking_message(self, message_str: str):
        pass                                                                     
        
                                                                       
                                                                                           
           
        try:
            message = json.loads(message_str)
            command = message.get("command")
            
            if command == "queued":
                                  
                avg_queue_time = message.get("avg_queue_time", 0)
                num_players = message.get("num_players_in_queue", 0)
                print(f"In queue. Average wait time: {avg_queue_time:.1f}s. Players in queue: {num_players}")
                
            elif command == "match_found":
                                                                                          
                self.game_url = message.get("game_url")
                self.env_id = message.get("env_id")                          
                self.environment_id = message.get("environment_id")
                
                                                                     
                                                                                                                      
                server_env_name = message.get("env_id")                                                
                
                                                                   
                self.matched_env_name = None
                for env_name in self.env_id_names:
                    if strip_env_variant(env_name) == strip_env_variant(server_env_name):
                        self.matched_env_name = env_name
                        break
                
                if not self.matched_env_name:
                                                       
                    self.matched_env_name = server_env_name
                
                print(f"Match found! Environment: {self.matched_env_name} (Server ID: {server_env_name})")
                print(f"Connecting to game server: {self.game_url}")
                self.matchmaking_complete = True
                
            elif command == "error":
                                           
                error_msg = message.get("message", "Unknown error")
                print(f"Matchmaking error: {error_msg}")
                
            elif command == "left":
                                                              
                print("Left matchmaking queue")
                
            else:
                print(f"Unknown matchmaking command: {command}")
                
        except json.JSONDecodeError:
            print(f"Invalid JSON received from matchmaking: {message_str}")

        except Exception as e:
            print(f"Error processing matchmaking message: {e}")

    async def connect_to_matchmaking(self):
        pass                                                                                        

                      
                                                                             
                                                                             
                                                     
                                                                             
           
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

                                            
        query_params = {
            "model_name": self.model_name,
            "model_token": self.model_token,
        }
        query_string = urlencode(query_params)
        ws_uri = f"{MATCHMAKING_WS_URI}?{query_string}"
        
        print(f"Connecting to matchmaking server: {ws_uri}")
        
        try:
                                         
            self.matchmaking_websocket = await websockets.connect(
                ws_uri,
                                                         
                ping_interval=20,
                ping_timeout=60
            )
            
                                                    
            asyncio.create_task(self._matchmaking_receiver())
            
                              
            queue_message = {
                "command": "queue",
                "environments": self.env_ids
            }
            await self.matchmaking_websocket.send(json.dumps(queue_message))
            print(f"Sent queue request for environments: {self.env_ids}")
            
                                                   
            start_time = asyncio.get_event_loop().time()
            while not self.matchmaking_complete:
                try:
                                                                        
                    message = await asyncio.wait_for(
                        self.matchmaking_queue.get(),
                        timeout=1.0
                    )
                    await self._process_matchmaking_message(message)

                except asyncio.TimeoutError:
                                                                
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > self.matchmaking_timeout:
                        print("Timeout waiting for match")
                        await self.matchmaking_websocket.close()
                        return False
                    continue
            
                                                                 
            try:
                await self.matchmaking_websocket.close()
            except:
                pass
                
            return self.game_url is not None
            
        except Exception as e:
            print(f"Matchmaking connection error: {e}")
            return False

    async def connect_to_game_server(self):
        pass                                                                          

                                                                                                
                                                                   
                                                          
                                                                         

                
                                                                 
           
        if not self.game_url:
            print("No game server IP available")
            return False
                
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
                                                      
        print("Waiting for game server to initialize...")
        await asyncio.sleep(2)

        ws_uri = f"wss://{self.game_url}/ws?token={self.model_token}"
        print(f"Connecting to game server: {ws_uri}")
        
        max_attempts, initial_grace_period = 15, 12
        start_time = asyncio.get_event_loop().time()
        
        for attempt in range(1, max_attempts + 1):
            try:
                self.websocket = await websockets.connect(
                    ws_uri,
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=90
                )
                
                asyncio.create_task(self._message_receiver())
                asyncio.create_task(self._action_sender())
                asyncio.create_task(self._ping_sender())
                
                elapsed_time = asyncio.get_event_loop().time() - start_time
                print(f"Connected to game server successfully after {elapsed_time:.1f}s")
                return True
                
            except Exception as e:
                elapsed_time = asyncio.get_event_loop().time() - start_time
                
                                                                 
                if elapsed_time > initial_grace_period:
                    print(f"Connection error (attempt {attempt}/{max_attempts}, {elapsed_time:.1f}s elapsed): {e}")
                else:
                                                                                   
                    if attempt % 3 == 0:                                         
                        print(f"Waiting for server... ({elapsed_time:.1f}s elapsed)")
                
                if attempt < max_attempts:
                                                                                   
                    if elapsed_time < initial_grace_period:
                        delay = 1                                     
                    else:
                        delay = min(3, 1 + (attempt - 1) * 0.5)                            
                    
                    await asyncio.sleep(delay)
                else:
                    total_elapsed = asyncio.get_event_loop().time() - start_time
                    print(f"All connection attempts failed after {total_elapsed:.1f}s")
                    return False

    async def connect(self):
        pass                                                                      
        
                                                            
                                       
                          
                                                          
                                                                        
        
                
                                                                 
           
                                      
        matchmaking_success = await self.connect_to_matchmaking()
        if not matchmaking_success:
            print("Failed to get a match")
            return False
            
                                         
        return await self.connect_to_game_server()

    async def _process_message(self, message_str: str):
        pass                                                                        
           
        try:
            message = json.loads(message_str)
            command = message.get("command")
            
            if command == "observation":
                                                                 
                serialized_observation = message.get("observation")
                player_id = message.get("player_id")
                
                print(f"Received observation for player {player_id}")
                self.current_player_id = player_id
                
                                                                                    
                                                                                          
                                                                            
                from textarena.core import ObservationType
                formatted_observation = []
                for sender_id, msg, obs_type_value in serialized_observation:
                                                                 
                    obs_type = ObservationType(obs_type_value)
                    formatted_observation.append((sender_id, msg, obs_type))
                
                self.current_observation = formatted_observation
                self.full_observations[player_id] = formatted_observation
                self.pending_action = False
                self.in_game = True

                self.step_info["player_id"] = player_id

                if player_id not in self.game_info:
                    self.game_info[player_id] = {"turn_count": 0, "invalid_move": False, "reason": ""}

                self.game_info[player_id]["turn_count"] += 1
                self.step_info["turn_count"] = self.game_info[player_id]["turn_count"]
                    
            elif command == "game_over":
                                                                    
                print("Game over received")
                self.game_over = True
                outcome = message.get("outcome", "unknown")
                reason = message.get("reason", "No reason provided")

                if self.current_player_id is not None:
                    self.rewards[self.current_player_id] = message.get("trueskill_change", 0)
                    self.game_info[self.current_player_id].update({
                        "reason": reason,
                        "outcome": outcome,
                        "invalid_move": self.game_info[self.current_player_id].get("invalid_move", False)
                    })

                self.step_info["game_end"] = True
                self.step_info["reason"] = reason
                self.step_info["outcome"] = outcome

                print(f"Game over: {outcome}, reason: {reason}")
                
            elif command == "timed_out":
                self.game_over = True
                timeout_msg = message.get("message", "Unknown timeout")

                if self.current_player_id is not None:
                    self.game_info[self.current_player_id].update({
                        "reason": "timeout",
                        "invalid_move": False
                    })

                self.step_info["timeout"] = True
                self.step_info["message"] = timeout_msg

            elif command == "error":
                error_msg = message.get("message", "Unknown error")
                print(f"Server error: {error_msg}")
                self.step_info["error"] = error_msg

            elif command == "action_ack":
                print("Action acknowledged by server")
                self.step_info["acknowledged"] = True
                
            elif command == "pong":
                pass
                
            elif command == "ping":
                try:
                    await self.websocket.send(json.dumps({"command": "pong"}))
                except Exception as e:
                    print(f"Error sending pong: {e}")
                    
            elif command == "server_shutdown":
                print("Server shutdown message received")
                self.server_shutdown = True
                
            else:
                print(f"Unknown command received: {command}")
                
        except json.JSONDecodeError:
            print(f"Invalid JSON received: {message_str}")

        except Exception as e:
            print(f"Error processing message: {e}")
            
    async def update_loop(self):
        pass                                    
        game_over_time = None
        
        while not self.server_shutdown:
            try:
                timeout = 5.0 if self.game_over else None
                
                try:
                                                       
                                                                            
                    message = await asyncio.wait_for(self.message_queue.get(), timeout=timeout)
                    await self._process_message(message)
                    
                                                                          
                    if self.game_over and game_over_time is None:
                        game_over_time = asyncio.get_event_loop().time()
                        print("Game over received, waiting for additional messages...")
                    
                except asyncio.TimeoutError:
                                                                                                 
                    if self.game_over:
                        elapsed = asyncio.get_event_loop().time() - game_over_time
                        print(f"Timeout after {elapsed:.1f}s while waiting for additional messages after game over")
                        
                        if elapsed > self.game_over_timeout:
                            print(f"No more messages after {self.game_over_timeout}s of game over, exiting loop")
                            self.server_shutdown = True

                    else:
                                                                           
                        print(f"Timeout while waiting for messages")
                        self.game_over = True
                        self.server_shutdown = True
                    
                                                                   
                if self.game_over and game_over_time is not None:
                    elapsed = asyncio.get_event_loop().time() - game_over_time
                    if elapsed > self.game_over_timeout:
                        print(f"No more messages after {self.game_over_timeout}s of game over, exiting loop")
                        self.server_shutdown = True
                    
            except websockets.exceptions.ConnectionClosed:
                print("WebSocket connection closed by server")
                self.server_shutdown = True                                                 
                break
                
            except Exception as e:
                print(f"Error in update loop: {e}")
                await asyncio.sleep(0.1)
                
        print("Update loop exiting")

    async def async_get_observation(self) -> Tuple[Optional[int], List]:
        pass                                                                                   

                                                                            
                                                                            
                                         
                               

                
                                                                                 
           
                                                      
        if self.current_player_id is not None and self.current_observation:
            observation = self.current_observation
            player_id = self.current_player_id
            return player_id, observation

        if not self.server_shutdown:
            if self.update_task is None or self.update_task.done():
                self.update_task = asyncio.create_task(self.update_loop())
            
            try:
                                                                       
                start_time = asyncio.get_event_loop().time()

                while not self.server_shutdown:
                    if self.current_player_id is not None and self.current_observation:
                        return self.current_player_id, self.current_observation
                    await asyncio.sleep(0.1)
                        
            except Exception as e:
                print(f"Error waiting for observation: {e}")
                    
        self.observation_valid = False
        return None, []

    def get_observation(self) -> Tuple[Optional[int], List]:
        pass                                                                                         
        
                                                    
                                                              
           
        try:
                                                        
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                new_loop = True
            else:
                new_loop = False
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            new_loop = True

        try:
                                                 
            player_id, obs = loop.run_until_complete(self.async_get_observation())

                                          
            if getattr(self, "observation_valid", True) is False:
                raise RuntimeError("No valid observation — server shutdown or invalid state.")

            return player_id, obs
        
        finally:
                                                    
            if new_loop:
                loop.close()

    async def async_step(self, action: str):
        pass                             
        if self.server_shutdown:
            return True, self.step_info

        self.step_info = {}

        if self.current_player_id is not None:
            self.step_info["player_id"] = self.current_player_id
            self.step_info["turn_count"] = self.game_info.get(self.current_player_id, {}).get("turn_count", 0) + 1

        await self.action_queue.put(action)
        await self.action_queue.join()
        self.current_observation = None

        while not self.server_shutdown and self.pending_action:
            await asyncio.sleep(0.1)

        return self.game_over, self.step_info

    def step(self, action: str):
        pass                                                                              

             
                                                                          

                
                                                                                             
           
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                new_loop = True
            else:
                new_loop = False
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            new_loop = True
            
        try:
            return loop.run_until_complete(self.async_step(action))
        finally:
            if new_loop:
                loop.close()

    async def async_reset(self, num_players=None, seed=None):
        pass                                               
        self.current_player_id = None
        self.current_observation = None
        self.game_over = False
        self.server_shutdown = False
        self.rewards = {}
        self.info = {}
        self.full_observations = {}
        self.in_game = False
        self.update_task = None
        self.matchmaking_complete = False
        
                                                                                
        if not self.websocket:
            connected = await self.connect()
            if not connected:
                print("Failed to connect to server")
                await self.async_close()
                return []
                
                                            
        self.update_task = asyncio.create_task(self.update_loop())
        
        try:
                                                                              
            start_time = asyncio.get_event_loop().time()
            while not self.server_shutdown and not self.in_game:
                await asyncio.sleep(0.1)
                
                if self.current_player_id is not None and self.current_observation:
                    self.in_game = True
                    return self.current_observation

        except Exception as e:
            print(f"Error waiting for game start: {e}")
                
                                                  
        return self.current_observation if self.current_observation else []

    def reset(self, num_players=None, seed=None):
        pass                                            

                
                                                  
           
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                new_loop = True
            else:
                new_loop = False
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            new_loop = True
            
        try:
            return loop.run_until_complete(self.async_reset(num_players))
        finally:
            if new_loop:
                loop.close()

    async def async_close(self):
        pass                                                                    
        
                      
                                           
                                          
                                                        
                                                 
                                        
           
                                                                
        self.server_shutdown = True
        
                                      
        try:
            await self.action_queue.put("CLOSE")
        except:
            pass
            
                                     
        if self.websocket and not getattr(self.websocket, 'closed', True):
            try:
                await self.websocket.close()
            except:
                pass
            
                                                   
        if self.matchmaking_websocket and not getattr(self.matchmaking_websocket, 'closed', True):
            try:
                await self.matchmaking_websocket.close()
            except:
                pass
                
                                       
        if self.update_task and not self.update_task.done():
            try:
                self.update_task.cancel()
            except:
                pass
                
        return self.rewards, self.game_info

    def close(self):
        pass                                            

                                                               

                
                                                      
           
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                new_loop = True
            else:
                new_loop = False

        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            new_loop = True
            
        try:
            return loop.run_until_complete(self.async_close())
        
        finally:
            if new_loop:
                loop.close()

def extract_agent_attributes(agent):
    pass                                                                     
    if agent is None:
        return None
    
    return {
        "agent_class": agent.__class__.__name__,
        "agent_model": getattr(agent, "model_name", getattr(agent, "model_id", "")),
        "system_prompt": getattr(agent, "system_prompt", ""),
        "extra": getattr(agent, "kwargs", {}) or getattr(agent, "generation_config", {}) or {}
    }

def get_deterministic_model_token(
    email: str, model_name: str, agent_attributes: dict
) -> str:
    pass                                                                                   
    namespace = uuid.NAMESPACE_DNS
    agent_class = agent_attributes["agent_class"]
    agent_model = agent_attributes["agent_model"]
    system_prompt = agent_attributes["system_prompt"]
    extra_str = str(sorted(agent_attributes["extra"].items()))
    combined = f"{email}|{model_name}|{agent_class}|{agent_model}|{system_prompt}|{extra_str}"
    return str(uuid.uuid5(namespace, combined))

def register_model(model_name: str, description: str, email: str, agent_obj=None) -> str:
    pass                                                               
    try:
                                                               
        model_token = None
        agent_attributes = extract_agent_attributes(agent_obj)
        model_token = get_deterministic_model_token(email, model_name, agent_attributes)
        
        payload = {"model_name": model_name, "description": description, "email": email, "model_token": model_token}
        
        response = requests.post(
            f"{MATCHMAKING_HTTP_URI}/register_model",
            json=payload
        )
        
                                                          
        if response.status_code == 409:            
            try:
                error_data = response.json()
                detail = error_data.get('detail', 'Model conflict')
                print(f"\n❌ Registration failed.")
                
                                                                       
                if "email (existing:" in detail: print("💡 Solution: This model name is taken - use the exact same email as your previous registration")
                elif "different token" in detail: print("💡 Solution: Agent configuration changed - use a different model name or revert agent settings")
                else: print("💡 Suggestion: Try using a different model name")
                return None
            except: print(f"\n❌ Model already exists with different configuration."); return None
                
        elif response.status_code == 400:               
            try:
                error_data = response.json()
                detail = error_data.get('detail', 'Invalid request')
                print(f"\n❌ Registration failed.")
                                                 
                if "Model token is required" in detail:
                    print("💡 Solution: Pass an agent object to make_online() to enable deterministic tokens:")
                    print("   Example:")
                    print("   agent = ta.agents.OpenRouterAgent(model_name='gpt-4o')")
                    print("   env = ta.make_online(..., agent_obj=agent)")
                elif "Invalid token format" in detail: print("💡 This is likely a bug - please report this issue")
                else: print("💡 Check your request parameters and try again")
                return None
            except: print(f"\n❌ Invalid request: {response.text}"); return None
                
        elif response.status_code != 200: print(f"\n❌ Server error ({response.status_code}): {response.text}"); return None
        
                      
        response.raise_for_status()
        data = response.json()
        return data.get("model_token")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network error registering model: {e}")
        return None

    except Exception as e:
        print(f"\n❌ Unexpected error registering model: {e}")
        return None


def make_online(
    env_id: Union[str, List[str]],
    model_name: str,
    model_token: Optional[str] = None,
    model_description: Optional[str] = None,
    email: Optional[str] = None,
    agent: Optional[object] = None,
) -> Union[OnlineEnvWrapper, DynamicWrapperProxy]:
    pass                                                                    

                              
    env_ids = [env_id] if isinstance(env_id, str) else env_id

                                         
    env_ids_int = []
    for full_id in env_ids:
        base_id = strip_env_variant(full_id)
        if base_id not in NAME_TO_ID_DICT:
            raise ValueError(f"Environment {full_id} not recognized (base: {base_id})")
        env_ids_int.append(NAME_TO_ID_DICT[base_id])

                               
    if not model_token:
        if not email or not agent:
            raise ValueError("Provide email and agent if model_token is not given.")
        model_token = register_model(model_name, model_description, email, agent)
        if not model_token:
            raise ValueError("Model registration failed.")
        print(f"✅ Registered '{model_name}' with {'deterministic' if agent else 'random'} token: {model_token}")
    else:
        print(f"✅ Using provided token for '{model_name}': {model_token}")

                         
    base_env = OnlineEnvWrapper(env_ids_int, env_ids, model_name, model_token)

                              
    env_id_to_wrappers = {}
    for name in env_ids:
        spec = ENV_REGISTRY.get(name)
        wrappers = spec.default_wrappers if spec and spec.default_wrappers else []
        env_id_to_wrappers[name] = wrappers
        if not spec:
            print(f"[make_online] Warning: '{name}' not found in ENV_REGISTRY")

                              
    print(f"{'Environment':<30} | Wrappers")
    print("-" * 70)
    for name in sorted(env_id_to_wrappers):
        wrappers = env_id_to_wrappers[name]
        wrapper_names = ", ".join(w.__name__ for w in wrappers) if wrappers else "None"
        print(f"{name:<30} | {wrapper_names}")
    print()

                                             
    if len(env_ids) == 1 and env_ids[0] in ENV_REGISTRY:
        wrappers = env_id_to_wrappers[env_ids[0]]
        if wrappers:
            print(f"[make_online] Applying wrappers for '{env_ids[0]}':")
            for wrapper in wrappers:
                print(f"  - {wrapper.__name__}")
                base_env = wrapper(base_env)
        return base_env

                                            
    return DynamicWrapperProxy(base_env, env_id_to_wrappers)



                                                  

MGC_NAME_TO_ID_DICT = {
    "SecretMafia-v0": 75,
    "Codenames-v0":  65,
    "ColonelBlotto-v0": 82,
    "ThreePlayerIPD-v0": 83,
}


                                                
def register_mgc_model(model_name: str, description: str, email: str, agent_obj=None, small_category: bool = False) -> str:
    pass                                                               
    try:
                                                               
        model_token = None
        agent_attributes = extract_agent_attributes(agent_obj)
        model_token = get_deterministic_model_token(email, model_name, agent_attributes)
        
        payload = {"model_name": model_name, "description": description, "email": email, "model_token": model_token, "small_category": small_category}
        
        response = requests.post(
            f"{MATCHMAKING_HTTP_URI}/register_mgc_model",
            json=payload
        )
        
                                                          
        if response.status_code == 409:            
            try:
                error_data = response.json()
                detail = error_data.get('detail', 'Model conflict')
                print(f"\n❌ Registration failed.")
                
                                                                       
                if "email (existing:" in detail: print("💡 Solution: This model name is taken - use the exact same team hash as your previous registration")
                elif "different token" in detail: print("💡 Solution: Agent configuration changed - use a different model name or revert agent settings")
                else: print("💡 Suggestion: Try using a different model name")
                return None
            except: print(f"\n❌ Model already exists with different configuration."); return None
                
        elif response.status_code == 400:               
            try:
                error_data = response.json()
                detail = error_data.get('detail', 'Invalid request')
                print(f"\n❌ Registration failed.")
                                                 
                if "Model token is required" in detail:
                    print("💡 Solution: Pass an agent object to make_mgc_online() to enable deterministic tokens:")
                    print("   Example:")
                    print("   agent = ta.agents.OpenRouterAgent(model_name='gpt-4o')")
                    print("   env = ta.make_mgc_online(..., agent_obj=agent)")
                elif "Invalid token format" in detail: print("💡 This is likely a bug - please report this issue")
                else: print("💡 Check your request parameters and try again")
                return None
            except: print(f"\n❌ Invalid request: {response.text}"); return None
                
        elif response.status_code != 200: print(f"\n❌ Server error ({response.status_code}): {response.text}"); return None
        
                      
        response.raise_for_status()
        data = response.json()
        return data.get("model_token")
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Network error registering model: {e}")
        return None

    except Exception as e:
        print(f"\n❌ Unexpected error registering model: {e}")
        return None


                                                                        
def make_mgc_online(
    track: str,
    model_name: str,
    model_token: Optional[str] = None,
    model_description: Optional[str] = None,
    team_hash: Optional[str] = None,
    agent: Optional[object] = None,
    small_category: bool = False
) -> OnlineEnvWrapper:
    pass                                                                             

                                                                                                        
                                                                                       

         
                                                                   
                                                                            
                                                                                                          
                                                                           
                                                                            
                                                                              
                                                                                 

            
                                                                                         

           
                                                                           

            
                              
                                   
                                   
                                                        
                                  
                                                       
                               
         
       


                              
    if track == "Social Detection":
        env_ids = ["SecretMafia-v0-train"]
    elif track == "Generalization":
        env_ids = ["Codenames-v0-train", "ColonelBlotto-v0-train", "ThreePlayerIPD-v0-train"]
    else:
        raise ValueError(f"Track '{track}' not recognized for Mind Games Challenge. Use 'Social Detection' or 'Generalization'.")

                                         
    env_ids_int = []
    for full_id in env_ids:
        base_id = strip_env_variant(full_id)
        if base_id not in MGC_NAME_TO_ID_DICT:
            raise ValueError(f"Environment {full_id} not recognized (base: {base_id} for MindGamesChallenge)")
        env_ids_int.append(MGC_NAME_TO_ID_DICT[base_id])

                               
    if not model_token:
        if not team_hash or not agent:
            raise ValueError("Provide email and agent if model_token is not given.")
        model_token = register_mgc_model(model_name, model_description, team_hash, agent, small_category)

        if not model_token:
            raise ValueError("Model registration failed.")
        print(f"✅ Registered '{model_name}' with {'deterministic' if agent else 'random'} token: {model_token}")
    else:
        print(f"✅ Using provided token for '{model_name}': {model_token}")

                         
    base_env = OnlineEnvWrapper(env_ids_int, env_ids, model_name, model_token)

                              
    env_id_to_wrappers = {}
    for name in env_ids:
        spec = ENV_REGISTRY.get(name)
        wrappers = spec.default_wrappers if spec and spec.default_wrappers else []
        env_id_to_wrappers[name] = wrappers
        if not spec:
            print(f"[make_online] Warning: '{name}' not found in ENV_REGISTRY")

                              
    print(f"{'Environment':<30} | Wrappers")
    print("-" * 70)
    for name in sorted(env_id_to_wrappers):
        wrappers = env_id_to_wrappers[name]
        wrapper_names = ", ".join(w.__name__ for w in wrappers) if wrappers else "None"
        print(f"{name:<30} | {wrapper_names}")
    print()

                                             
    if len(env_ids) == 1 and env_ids[0] in ENV_REGISTRY:
        wrappers = env_id_to_wrappers[env_ids[0]]
        if wrappers:
            print(f"[make_online] Applying wrappers for '{env_ids[0]}':")
            for wrapper in wrappers:
                print(f"  - {wrapper.__name__}")
                base_env = wrapper(base_env)
        return base_env

                                            
    return DynamicWrapperProxy(base_env, env_id_to_wrappers)