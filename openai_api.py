# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import openai
from multiprocessing.pool import ThreadPool
import threading


class Timer(object):
    def __init__(self):
        self.__start = time.time()

    def start(self):
        self.__start = time.time()

    def get_time(self, restart=True, format=False):
        end = time.time()
        span = end - self.__start
        if restart:
            self.__start = end
        if format:
            return self.format(span)
        else:
            return span

    def format(self, seconds):
        return datetime.timedelta(seconds=int(seconds))

    def print(self, name):
        print(name, self.get_time())


openai.api_type = "azure"
openai.api_version = "2023-03-15-preview"

# fill in your OpenAI API key in the {} below, format: "custum_api_name": "your_api_key"
API_dic = {}

API_name_key_list = list(API_dic.items())
default_engine = None

API_ID=0
lock = threading.Lock()
def set_next_API_ID():
    global API_ID
    lock.acquire()
    # print("API_ID", API_ID)
    API_ID = (API_ID + 1) % len(API_name_key_list)
    openai.api_base = "https://{0}.openai.azure.com/".format(API_name_key_list[API_ID][0])
    openai.api_key = API_name_key_list[API_ID][1]
    lock.release()


set_next_API_ID()


def multi_threading_running(func, queries, n=20, multiple_API=True):
    # @backoff.on_exception(backoff.expo, openai.error.RateLimitError)
    def wrapped_function(query, max_try=20):
        if multiple_API:
            set_next_API_ID()
        try:
            result = func(query)
            return result
        except (openai.error.RateLimitError, openai.error.APIError) as e:
            if not isinstance(e, openai.error.RateLimitError):
                if isinstance(e, openai.error.APIError):
                    print("API Error")
                else:
                    print("found a error:", e)
            if max_try > 0:
                return wrapped_function(query, max_try-1)

    pool = ThreadPool(n)
    replies = pool.map(wrapped_function, queries)
    return replies


cache = {}
def query_azure_openai_chat(query, engine="gpt-35-turbo"):
    global default_engine, cache
    query_string = json.dumps(query)
    if query_string in cache:
        return cache[query_string]
    if default_engine is not None:
        engine = default_engine
    if engine == "chatgpt":
        engine = "gpt-35-turbo"
    try:
        messages = [
                       {"role": "system", "content": "You are a helpful AI assistant."},
                   ]
        if isinstance(query, str):
            messages.append(
                {"role": "user", "content": query},
            )
        elif isinstance(query, list):
            messages += query
        else:
            raise ValueError("Unsupported query: {0}".format(query))
        response = openai.ChatCompletion.create(
            engine=engine,  # The deployment name you chose when you deployed the ChatGPT or GPT-4 model.
            messages=messages,
            temperature=0,
            stop=["<|im_end|>"]
        )
    except TypeError as e:
        print("type error:", e)
        return {'choices': [{'message': {'content': ""}}]}
    try:
        if response['choices'][0]['message']['content'] != "":
            cache[query_string] = response
    except Exception as e:
        pass
    return response # ['choices'][0]['message']['content']


def query_azure_openai_complete(query, engine="gpt-35-turbo"):
    if engine == 'chatgpt':
        engine = "gpt-35-turbo"
    try:
        response = openai.Completion.create(
            engine=engine,
            prompt=query,
            max_tokens=2000,
            temperature=0,
            stop=["<END>"])
    except TypeError as e:
        print(e)
        return {"choices": [{"text": ""}]}
    return response
    # return response["choices"][0]["text"]


import time
import datetime

class Timer(object):

    def __init__(self):
        self.__start = time.time()

    def start(self):
        self.__start = time.time()

    def get_time(self, restart=True, format=False):
        end = time.time()
        span = end - self.__start
        if restart:
            self.__start = end
        if format:
            return self.format(span)
        else:
            return span * 1000

    def format(self, seconds):
        return datetime.timedelta(seconds=int(seconds))

    def print(self, name):
        print(name, self.get_time())


def test_speed_1():
    import json
    path = "khan/topic_19.jsonal"

    questions = []
    timer = Timer()
    with open(path) as reader:
        for i, line in enumerate(reader):
            js = json.loads(line.strip())
            question = js["Question"]
            questions.append(question)

    questions = questions[:100]
    reply = multi_threading_running(query_azure_openai_complete, questions, n=50, multiple_API=True)
    print("Average time after {0} samples: {1}".format(len(questions), timer.get_time(restart=False) / len(questions)))


def test_speed_2():
    import json
    path = r"D:\Datasets\AGIEval\outputs\model_output\english_choice\sat_math\turbo_few\test_sat_math_gpt-35-turbo_cot_False_few.jsonl"
    with open(path, encoding='utf8') as reader:
        questions = []
        for line in reader:
            js = json.loads(line.strip())
            questions.append(js["Question"])
    timer = Timer()
    results = multi_threading_running(query_azure_openai_complete, questions, n=50, multiple_API=True)
    print("Average time after {0} samples: {1}".format(len(questions), timer.get_time(restart=False) / len(questions)))
    # results = pool.map(query_azure_openai, questions)
    with open('output.txt', 'w') as writer:
        for result in results:
            writer.write(json.dumps(result) + '\n')


if __name__ == "__main__":
    API_ID=0
    for i in range(len(API_name_key_list)):
        set_next_API_ID()
        print(query_azure_openai_chat("1+1", engine='gpt-4'))
    # test_speed_2()

