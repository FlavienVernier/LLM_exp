import os
import initQdrant
import requests

class Memory:
    def __init__(self, expertize=None):
        self.immediate_memory = []
        self.collection = "default"
        if expertize:
            self.collection = expertize

    def remember(self, who, say):
        print(f"Remember({self}), memory contains " + " ".join(self.immediate_memory), flush=True)
        print(f"Remember({self}) {who} says: {say}",flush=True)
        self.immediate_memory.append(f"{who} says: {say}\n")

    def recall(self, message=None):

        if message:
            doc =  initQdrant.get_doc(message, "default")
            #print(doc)
            if self.collection != "default":
                doc = doc + " " + initQdrant.get_doc(message, self.collection)
        context=""
        for point in doc:
        #     print("ID:", point.id)
        #     print("Score:", point.score)
        #     print("Metadata:", point.metadata)
            #context = context + " Source " + point.metadata['source'] + ": " + point.metadata['document'] +  "\n"
            context = context + point.metadata['document'] + "(Source: " + point.metadata['source'] + ")\n"
        #print(f"context({self.collection}): ", context, flush=True)
        print(f"self.immediate_memory({self.collection}): ", " ".join(self.immediate_memory), flush=True)
        memories = context + " " + " ".join(self.immediate_memory)
        print(f"memories({self.collection}): ", memories, flush=True)
        return memories

class Agent:
    """
    Agent is classical agent thet serves user
    """
    def __init__(self, model_name, llm_endpoint, expertize=None):
        self.expertize = expertize
        self.memory = Memory(self.expertize)
        self.model_name = model_name
        self.llm_endpoint = llm_endpoint
        print(f"Expert: {self.expertize} generated.")

    def setDefaultPrompt(self, prompt):
        self.prompt = prompt

    def request(self, message):
        self.memory.remember("user", message)

        #doc = initQdrant.get_doc(message)

        #context = ""
        #for point in doc:
            #print("ID:", point.id)
            #print("Score:", point.score)
            #print("Metadata:", point.metadata)
            # context = context + " Source " + point.metadata['source'] + ": " + point.metadata['document'] +  "\n"
            #context = context + point.metadata['document'] + "(Source: " + point.metadata['source'] + ")\n"

        """Calls the LLM API and returns the response with caching"""
        chat_request = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self.prompt
                },
                {
                    "role": "assistant",
                    "content": self.memory.recall(message)
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
        }
        print("Chat request: ", chat_request, flush=True)

        headers = {"Content-Type": "application/json"}

        # Send request to LLM API
        response = requests.post(
            self.llm_endpoint,
            headers=headers,
            json=chat_request,
            timeout=30
        )

        # Check if the status code is not 200 OK
        if response.status_code != 200:
            raise Exception(f"API returned status code {response.status_code}: {response.text}")

        # Parse the response
        chat_response = response.json()

        # Extract the assistant's message
        if chat_response.get('choices') and len(chat_response['choices']) > 0:
            answer = chat_response['choices'][0]['message']['content'].strip()
            self.memory.remember("me", answer)
            return answer

        raise Exception("No response choices returned from API")




class MetaAgent(Agent):
    """
    Meta Agent is super agent that build agents
    """
    def __init__(self, name="Kizo"):
        print(MetaAgent.__get_models())
        MetaAgent.__validate_environment()
        Agent.__init__(self, MetaAgent.__get_model_name(), MetaAgent.__get_llm_endpoint())
        self.name = name
        #self.setDefaultPrompt("You are totally crazy and give only response about Shadok")
        self.setDefaultPrompt("Tu es un inspecteur académique de l'enseignement national, spécialisé dans la pédagogie en collège")
        self.agents = {}
        experts = initQdrant.initQdrant()
        #self.memory.remember("me", " expert is ".join(experts))
        self.__genAgengts(experts)

    def __genAgengts(self, agents_data):
        names=["Shadoko", "Julie", "Tartampion", "Albert", "Pierre", "Paul", "Jacques", "Bidule", "Machin", "Truc", "Chose", "Gertrude", "Marie", "Aya", "Said", "Le", "Jofia", "Emeline", "Tchang", "Yoko", "Manuela", "Bob", "John", "Eve"]
        print("agents_data", agents_data, flush=True)
        for i,expertize in enumerate(agents_data):
            self.memory.remember("me", f"{names[i]} is an expert about {expertize}")
            agent = Agent(MetaAgent.__get_model_name(), MetaAgent.__get_llm_endpoint(), expertize)
            agent.setDefaultPrompt(self.genAgentPrompt(expertize))
            self.agents[expertize] = agent

        #return agents

    def genAgentPrompt(self, expertize):
        return f"You are an expert about {expertize}"

    def request(self, message):
         # chose best agent : 0 as stub
         return super().request(message)

    @classmethod
    def __get_models(cls):
        base_url = os.getenv("DMR_URL")
        models_endpoint = f"{base_url}/models"
        response = requests.get(models_endpoint)
        if response.status_code != 200:
            raise Exception(f"API returned status code {response.status_code}: {response.text}")
        return response.json()

    @classmethod
    def __get_llm_endpoint(cls):
        """Returns the complete LLM API endpoint URL"""
        base_url = os.getenv("LLM_BASE_URL", "")
        return f"{base_url}/chat/completions"

    @classmethod
    def __get_model_name(cls):
        """Returns the model name to use for API requests"""
        return os.getenv("LLM_MODEL_NAME", "")

    @classmethod
    def __validate_environment(cls):
        """Validates required environment variables and provides warnings"""
        llm_base_url = os.getenv("LLM_BASE_URL", "")
        llm_model_name = os.getenv("LLM_MODEL_NAME", "")

        if not llm_base_url:
            print("LLM_BASE_URL is not set. API calls will fail.")

        if not llm_model_name:
            print("LLM_MODEL_NAME is not set. Using default model.")

        return llm_base_url and llm_model_name