                                                  
                                                                      
   

class Conversation:
    def __init__(self, name, roles=("user", "assistant")):
        self.name = name
        self.roles = roles
        self.messages = []
        self.system_message = ""

    def append_message(self, role, message):
        self.messages.append([role, message])

    def to_openai_api_messages(self):
        messages = []
        if self.system_message:
            messages.append({"role": "system", "content": self.system_message})
        
        for role, message in self.messages:
                                        
                                                    
            api_role = role
            if role == self.roles[0]:
                api_role = "user"
            elif role == self.roles[1]:
                api_role = "assistant"
            
            if message:
                messages.append({"role": api_role, "content": message})
        
        return messages

def get_conv_template(name):
    pass                                
                                                                           
                                               
       
    return Conversation(name, roles=("user", "assistant"))
