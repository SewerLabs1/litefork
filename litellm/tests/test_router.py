#### What this tests ####
#This tests litellm router

import sys, os, time
import traceback, asyncio
import pytest
sys.path.insert(
    0, os.path.abspath("../..")
)  # Adds the parent directory to the system path
import litellm
from litellm import Router
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

def test_exception_raising():
	# this tests if the router raises an exception when invalid params are set
	# in this test both deployments have bad keys - Keep this test. It validates if the router raises the most recent exception
	litellm.set_verbose=True
	import openai
	try:
		print("testing if router raises an exception")
		old_api_key = os.environ["AZURE_API_KEY"]
		os.environ["AZURE_API_KEY"] = ""
		model_list = [
			{ 
				"model_name": "gpt-3.5-turbo", # openai model name 
				"litellm_params": { # params for litellm completion/embedding call 
					"model": "azure/chatgpt-v-2", 
					"api_key": "bad-key",
					"api_version": os.getenv("AZURE_API_VERSION"),
					"api_base": os.getenv("AZURE_API_BASE")
				},
				"tpm": 240000,
				"rpm": 1800
			},
			{
				"model_name": "gpt-3.5-turbo", # openai model name 
				"litellm_params": { #
					"model": "gpt-3.5-turbo", 
					"api_key": "bad-key",
				},
				"tpm": 240000,
				"rpm": 1800
			}
		]
		router = Router(model_list=model_list, 
					redis_host=os.getenv("REDIS_HOST"), 
					redis_password=os.getenv("REDIS_PASSWORD"), 
					redis_port=int(os.getenv("REDIS_PORT")), 
					routing_strategy="simple-shuffle",
					set_verbose=False,
					num_retries=1) # type: ignore
		response = router.completion(
			model="gpt-3.5-turbo",
			messages=[
				{
					"role": "user",
					"content": "hello this request will fail"
				}
			]
		)
		os.environ["AZURE_API_KEY"] = old_api_key
		pytest.fail(f"Should have raised an Auth Error")
	except openai.AuthenticationError:
		print("Test Passed: Caught an OPENAI AUTH Error, Good job. This is what we needed!")
		os.environ["AZURE_API_KEY"] = old_api_key
		router.reset()
	except Exception as e:
		os.environ["AZURE_API_KEY"] = old_api_key
		print("Got unexpected exception on router!", e)
# test_exception_raising()


def test_reading_key_from_model_list():
	# [PROD TEST CASE]
	# this tests if the router can read key from model list and make completion call, and completion + stream call. This is 90% of the router use case
	# DO NOT REMOVE THIS TEST. It's an IMP ONE. Speak to Ishaan, if you are tring to remove this
	litellm.set_verbose=False
	import openai
	try:
		print("testing if router raises an exception")
		old_api_key = os.environ["AZURE_API_KEY"]
		os.environ.pop("AZURE_API_KEY", None)
		model_list = [
			{ 
				"model_name": "gpt-3.5-turbo", # openai model name 
				"litellm_params": { # params for litellm completion/embedding call 
					"model": "azure/chatgpt-v-2", 
					"api_key": old_api_key,
					"api_version": os.getenv("AZURE_API_VERSION"),
					"api_base": os.getenv("AZURE_API_BASE")
				},
				"tpm": 240000,
				"rpm": 1800
			}
		]

		router = Router(model_list=model_list, 
					redis_host=os.getenv("REDIS_HOST"), 
					redis_password=os.getenv("REDIS_PASSWORD"), 
					redis_port=int(os.getenv("REDIS_PORT")), 
					routing_strategy="simple-shuffle",
					set_verbose=True,
					num_retries=1) # type: ignore
		response = router.completion(
			model="gpt-3.5-turbo",
			messages=[
				{
					"role": "user",
					"content": "hello this request will fail"
				}
			]
		)
		print("\n response", response)

		print("\n Testing streaming response")
		response = router.completion(
			model="gpt-3.5-turbo",
			messages=[
				{
					"role": "user",
					"content": "hello this request will fail"
				}
			],
			stream=True
		)
		for chunk in response:
			if chunk is not None:
				print(chunk)
		print("\n Passed Streaming")
		os.environ["AZURE_API_KEY"] = old_api_key
		router.reset()
	except Exception as e:
		os.environ["AZURE_API_KEY"] = old_api_key
		print(f"FAILED TEST")
		pytest.fail(f"Got unexpected exception on router! - {e}")
# test_reading_key_from_model_list()



def test_router_azure_acompletion():
	# [PROD TEST CASE]
	# This is 90% of the router use case, makes an acompletion call, acompletion + stream call and verifies it got a response
	# DO NOT REMOVE THIS TEST. It's an IMP ONE. Speak to Ishaan, if you are tring to remove this
	litellm.set_verbose=False
	import openai
	try:
		print("Router Test Azure - Acompletion, Acompletion with stream")

		# remove api key from env to repro how proxy passes key to router 
		old_api_key = os.environ["AZURE_API_KEY"]
		os.environ.pop("AZURE_API_KEY", None)
	
		model_list = [
			{ 
				"model_name": "gpt-3.5-turbo", # openai model name 
				"litellm_params": { # params for litellm completion/embedding call 
					"model": "azure/chatgpt-v-2", 
					"api_key": old_api_key,
					"api_version": os.getenv("AZURE_API_VERSION"),
					"api_base": os.getenv("AZURE_API_BASE")
				},
				"rpm": 1800
			},
			{
				"model_name": "gpt-3.5-turbo", # openai model name 
				"litellm_params": { # params for litellm completion/embedding call 
					"model": "azure/gpt-turbo", 
					"api_key": os.getenv("AZURE_FRANCE_API_KEY"),
					"api_version": os.getenv("AZURE_API_VERSION"),
					"api_base": "https://openai-france-1234.openai.azure.com"
				},
				"rpm": 1800
			}
		]

		router = Router(model_list=model_list, 
					routing_strategy="simple-shuffle",
					set_verbose=True
				) # type: ignore
		
		async def test1():

			response = await router.acompletion(
				model="gpt-3.5-turbo",
				messages=[
					{
						"role": "user",
						"content": "hello this request will fail"
					}
				]
			)
			print("\n response", response)
		asyncio.run(test1())

		print("\n Testing streaming response")
		async def test2():
			response = await router.acompletion(
				model="gpt-3.5-turbo",
				messages=[
					{
						"role": "user",
						"content": "hello this request will fail"
					}
				],
				stream=True
			)
			async for chunk in response:
				if chunk is not None:
					print(chunk)
		asyncio.run(test2())
		print("\n Passed Streaming")
		os.environ["AZURE_API_KEY"] = old_api_key
		router.reset()
	except Exception as e:
		os.environ["AZURE_API_KEY"] = old_api_key
		print(f"FAILED TEST")
		pytest.fail(f"Got unexpected exception on router! - {e}")
test_router_azure_acompletion()

### FUNCTION CALLING 

def test_function_calling(): 
	model_list = [
		{
			"model_name": "gpt-3.5-turbo-0613",
			"litellm_params": {
				"model": "gpt-3.5-turbo-0613",
				"api_key": os.getenv("OPENAI_API_KEY"),
			},
			"tpm": 100000,
			"rpm": 10000,
		},
	]

	messages = [
		{"role": "user", "content": "What is the weather like in Boston?"}
	]
	functions = [
		{
		"name": "get_current_weather",
		"description": "Get the current weather in a given location",
		"parameters": {
			"type": "object",
			"properties": {
			"location": {
				"type": "string",
				"description": "The city and state, e.g. San Francisco, CA"
			},
			"unit": {
				"type": "string",
				"enum": ["celsius", "fahrenheit"]
			}
			},
			"required": ["location"]
		}
		}
	]

	router = Router(model_list=model_list, routing_strategy="latency-based-routing")
	response = router.completion(model="gpt-3.5-turbo-0613", messages=messages, functions=functions)
	router.reset()
	print(response)

def test_acompletion_on_router(): 
	try:
		litellm.set_verbose = False
		model_list = [
			{
				"model_name": "gpt-3.5-turbo",
				"litellm_params": {
					"model": "gpt-3.5-turbo-0613",
					"api_key": os.getenv("OPENAI_API_KEY"),
				},
				"tpm": 100000,
				"rpm": 10000,
			},
			{
				"model_name": "gpt-3.5-turbo",
				"litellm_params": {
					"model": "azure/chatgpt-v-2",
					"api_key": os.getenv("AZURE_API_KEY"),
					"api_base": os.getenv("AZURE_API_BASE"),
					"api_version": os.getenv("AZURE_API_VERSION")
				},
				"tpm": 100000,
				"rpm": 10000,
			}
		]

		messages = [
			{"role": "user", "content": f"write a one sentence poem {time.time()}?"}
		]
		start_time = time.time()
		router = Router(model_list=model_list, 
				redis_host=os.environ["REDIS_HOST"], 
				redis_password=os.environ["REDIS_PASSWORD"], 
				redis_port=os.environ["REDIS_PORT"], 
				cache_responses=True, 
				timeout=30,
				routing_strategy="simple-shuffle")
		async def get_response(): 
			response1 = await router.acompletion(model="gpt-3.5-turbo", messages=messages)
			print(f"response1: {response1}")
			response2 = await router.acompletion(model="gpt-3.5-turbo", messages=messages)
			print(f"response2: {response2}")
			assert response1.id == response2.id
			assert len(response1.choices[0].message.content) > 0
			assert response1.choices[0].message.content == response2.choices[0].message.content
		asyncio.run(get_response())
		router.reset()
	except litellm.Timeout as e: 
		end_time = time.time()
		print(f"timeout error occurred: {end_time - start_time}")
		pass
	except Exception as e:
		traceback.print_exc()
		pytest.fail(f"Error occurred: {e}")

# test_acompletion_on_router() 

def test_function_calling_on_router(): 
	try: 
		litellm.set_verbose = True
		model_list = [
            {
                "model_name": "gpt-3.5-turbo",
                "litellm_params": {
                    "model": "gpt-3.5-turbo-0613",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                },
            },
        ]
		function1 = [
            {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            }
        ]
		router = Router(
			model_list=model_list,
			redis_host=os.getenv("REDIS_HOST"),
			redis_password=os.getenv("REDIS_PASSWORD"),
			redis_port=os.getenv("REDIS_PORT")
		)
		messages=[
                {
                    "role": "user",
                    "content": "what's the weather in boston"
                }
            ]
		response = router.completion(model="gpt-3.5-turbo", messages=messages, functions=function1)
		print(f"final returned response: {response}")
		router.reset()
		assert isinstance(response["choices"][0]["message"]["function_call"], dict)
	except Exception as e: 
		print(f"An exception occurred: {e}")

# test_function_calling_on_router()

def test_aembedding_on_router():
	litellm.set_verbose = True
	try:
		model_list = [
			{
				"model_name": "text-embedding-ada-002",
				"litellm_params": {
					"model": "text-embedding-ada-002",
				},
				"tpm": 100000,
				"rpm": 10000,
			},
		]

		async def embedding_call():
			router = Router(model_list=model_list)
			response = await router.aembedding(
				model="text-embedding-ada-002",
				input=["good morning from litellm", "this is another item"],
			)
			print(response)
			router.reset()
		asyncio.run(embedding_call())
	except Exception as e:
		traceback.print_exc()
		pytest.fail(f"Error occurred: {e}")
# test_aembedding_on_router()


def test_azure_embedding_on_router():
	"""
	[PROD Use Case] - Makes an aembedding call + embedding call
	"""
	litellm.set_verbose = True
	try:
		model_list = [
			{
				"model_name": "text-embedding-ada-002",
				"litellm_params": {
					"model": "azure/azure-embedding-model",
					"api_key":os.environ['AZURE_API_KEY'],
					"api_base": os.environ['AZURE_API_BASE']
				},
				"tpm": 100000,
				"rpm": 10000,
			},
		]
		router = Router(model_list=model_list)

		async def embedding_call():
			response = await router.aembedding(
				model="text-embedding-ada-002",
				input=["good morning from litellm"]
			)
			print(response)
		asyncio.run(embedding_call())

		print("\n Making sync Azure Embedding call\n")

		response = router.embedding(
				model="text-embedding-ada-002",
				input=["test 2 from litellm. async embedding"]
		)
		print(response)
		router.reset()
	except Exception as e:
		traceback.print_exc()
		pytest.fail(f"Error occurred: {e}")
test_azure_embedding_on_router()


def test_bedrock_on_router():
	litellm.set_verbose = True
	print("\n Testing bedrock on router\n")
	try:
		model_list = [
			{
				"model_name": "claude-v1",
				"litellm_params": {
					"model": "bedrock/anthropic.claude-instant-v1",
				},
				"tpm": 100000,
				"rpm": 10000,
			},
		]

		async def test():
			router = Router(model_list=model_list)
			response = await router.acompletion(
				model="claude-v1",
				messages=[
					{
						"role": "user",
						"content": "hello from litellm test",
					}
				]
			)
			print(response)
			router.reset()
		asyncio.run(test())
	except Exception as e:
		traceback.print_exc()
		pytest.fail(f"Error occurred: {e}")
# test_bedrock_on_router()