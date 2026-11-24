                                   

                                                                                
                                              

                            
                                                                                           
                                                                                      
                                                                                           
                                                                                          

                                                                              
   
import requests
import json
import os
import traceback
from players.base_player import Player

class HTTPPlayer(Player):
    def __init__(self, url, public_name="HTTP Player", delta=None, player_id=0):
        super().__init__(public_name, delta, player_id)
        self.url = url
        self.messages = []
        self.system_message = ""
        self.api_key = self._load_api_key()

    def _load_api_key(self):
        keys_file = "http_keys.json"
        if os.path.exists(keys_file):
            try:
                with open(keys_file, "r") as f:
                    keys = json.load(f)
                                                                 
                return keys.get(self.url) or keys.get(self.url.rstrip('/'))
            except Exception as e:
                print(f"Error loading keys file: {e}")
        return None

    def add_message(self, message, role):
        self.messages.append({"role": role, "content": message})

    def get_text_answer(self, format_checker, decision=False):
                                                                                          
                                                 

        payload_game_params = {
            "public_name": self.public_name,
            "delta": self.delta,
            "player_id": self.player_id,
            "rules": self.rules,
            "req_offer_text": self.req_offer_text,
            "req_decision_text": self.req_decision_text,
        }

        if hasattr(self, 'game_params') and self.game_params:
            payload_game_params.update(self.game_params)

        payload = {
            "messages": self.messages,
            "decision": decision,
            "game_params": payload_game_params
        }

        headers = {}
        if self.api_key:
            headers['X-API-Key'] = self.api_key

        response = None
        try:
            response = requests.post(f"{self.url}/chat", json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            answer = data.get("response", "")

                                                         
            self.add_message(answer, "assistant")
            return answer

        except requests.exceptions.Timeout as e:
                                      
            print(f"[HTTP_ERROR] Timeout for player {self.public_name}")
            print(f"  URL: {self.url}")
            print(f"  Timeout: {self.timeout}s")
            print(f"  Last message sent: {self.messages[-1] if self.messages else 'None'}")
            raise e

        except requests.exceptions.HTTPError as e:
                                         
            print(f"[HTTP_ERROR] HTTP error for player {self.public_name}: {e}")
            print(f"  URL: {self.url}")
            print(f"  Status Code: {e.response.status_code if e.response else 'Unknown'}")
            response_text = e.response.text[:500] if e.response else 'No response'
            print(f"  Response Body: {response_text}")
            print(f"  Request Payload Keys: {list(payload.keys())}")
            print(f"  Message History Length: {len(self.messages)}")
            return ""

        except json.JSONDecodeError as e:
                                                 
            print(f"[HTTP_ERROR] JSON decode error for player {self.public_name}: {e}")
            print(f"  URL: {self.url}")
            if response is not None:
                print(f"  Response Status: {response.status_code}")
                print(f"  Response Text: {response.text[:500]}")
            return ""

        except requests.exceptions.ConnectionError as e:
                                               
            print(f"[HTTP_ERROR] Connection error for player {self.public_name}: {e}")
            print(f"  URL: {self.url}")
            print(f"  Suggestion: Check if the HTTP server is running and accessible")
            return ""

        except Exception as e:
                                            
            print(f"[HTTP_ERROR] Error communicating with HTTP player {self.public_name}: {e}")
            print(f"  URL: {self.url}")
            print(f"  Exception Type: {type(e).__name__}")
            print(f"  Traceback: {traceback.format_exc()[:500]}")
            return ""

    def clean_conv(self):
        self.messages = []
        if self.system_message:
            self.messages.append({"role": "system", "content": self.system_message})

    def set_system_message(self, message):
        self.system_message = message
                                                                  
        if not self.messages:
            self.messages.append({"role": "system", "content": message})
        elif self.messages[0]["role"] == "system":
            self.messages[0]["content"] = message
        else:
            self.messages.insert(0, {"role": "system", "content": message})
