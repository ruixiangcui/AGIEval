# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import openai_api
from src import utils, dataset_loader
import os
import openai


def query_openai(context_list, setting_name, n_multiply=3):
    n = len(openai_api.API_name_key_list) * n_multiply
    try:
        print("multi-thread n =", n)
        if setting_name == 'complete':
            results = openai_api.multi_threading_running(
                openai_api.query_azure_openai_complete, context_list, n=n)
        else:
            results = openai_api.multi_threading_running(
                openai_api.query_azure_openai_chat, context_list, n=n)
    except openai.error.APIConnectionError as e:
        print("found error:", e)
        return query_openai(context_list, setting_name, max(max(n_multiply-5, n_multiply//2), 1))
    return results


def query_openai_with_retry(context_list, setting_name, retry_time=4, results=None):
    if results is None:
        results = query_openai(context_list, setting_name)
    while retry_time > 0:
        filtered_context_list = []
        for i in range(len(results)):
            if utils.extract_answer(results[i]) == "":
                filtered_context_list.append(context_list[i])
        if len(filtered_context_list) == 0:
            # print("nothing need to retry")
            break

        filtered_results = query_openai(filtered_context_list, setting_name)

        p = 0
        for i in range(len(results)):
            if utils.extract_answer(results[i]) == "":
                results[i] = filtered_results[p]
                p += 1
        assert p == len(filtered_results)

        retry_succeeded = 0
        for item in filtered_results:
            if utils.extract_answer(item) != "":
                retry_succeeded += 1
        print("In the retry, {0} samples succeeded, {1} samples failed".format(
            retry_succeeded, len(filtered_results) - retry_succeeded))
        if retry_succeeded <= 3:
            retry_time -= 1
    assert len(results) == len(context_list)
    return results


def run_multiple_dataset_batch(work_items):
    if len(work_items) == 0:
        return
    print("work items:", work_items)
    dataset_list = []
    item_list = []
    for (input_path, output_path, mode, _) in work_items:
        assert mode == work_items[0][2]
        js_list = utils.read_jsonl(input_path)
        content_list = [item["context"] for item in js_list]
        dataset_list.append(len(content_list))
        item_list += content_list

    results = query_openai_with_retry(context_list=item_list, setting_name=work_items[0][2])

    s = 0
    for i in range(len(dataset_list)):
        utils.save_jsonl(results[s:s + dataset_list[i]], work_items[i][1])
        s += dataset_list[i]
    assert s == len(results)


def run_multiple_dataset(work_items):
    batch = []
    count = 0
    batch_size = 1000
    if openai_api.default_engine == 'gpt-4':
        batch_size = 500
    for item in work_items:
        if os.path.exists(item[1]):
            if len(utils.read_jsonl(item[1])) == item[3]:
                continue
        if count + item[3] > batch_size:
            run_multiple_dataset_batch(batch)
            batch = []
            count = 0
        batch.append(item)
        count += item[3]
    if len(batch) > 0:
        run_multiple_dataset_batch(batch)


if __name__ == "__main__":
    run_experiment = True
    dataset_dir = "data/v1"
    raw_prompt_path = "./data/few_shot_prompts.csv"
    output_dir = "./outputs/davinci-003"
    gpt_model = "davinci-003"
    openai_api.default_engine = gpt_model
    os.makedirs(os.path.join(output_dir, "inputs"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "outputs"), exist_ok=True)

    # dataset_name_list = ["gaokao-english"]
    dataset_name_list = [
        "gaokao-chinese",
        "gaokao-geography",
        "gaokao-history",
        "gaokao-biology",
        "gaokao-chemistry",
        "gaokao-physics",
        "gaokao-mathqa",
        "gaokao-english",
        "sat-math",
        "sat-en", "aqua-rat",
        "lsat-ar", "lsat-lr", "lsat-rc",
        "logiqa-en", "logiqa-zh",
        "gaokao-mathcloze",
        "jec-qa-kd", "jec-qa-ca",
        "math",
        "sat-en-without-passage",
    ]
    setting_name_list = [
        # 'few-shot', 'few-shot-CoT',
        'zero-shot',
        'zero-shot-CoT'
    ]
    skip_stage_1 = False
    skip_stage_2 = True
    skip_stage_3 = False

    chat_mode = True
    work_items = []
    for dataset_name in dataset_name_list:
        for setting_name in setting_name_list:
            dataset = dataset_loader.load_dataset(
                dataset_name, setting_name, dataset_dir,
                prompt_path=raw_prompt_path, max_tokens=2048,
                end_of_example="<END>\n", verbose=True, chat_mode=chat_mode)
            # dataset = dataset[:10]
            input_path = os.path.join(output_dir, "inputs", f"{dataset_name}.{setting_name}.jsonl")
            utils.save_jsonl(dataset, input_path)
            # dataset = dataset[:10]
            # print(dataset[0]['context'])
            output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.jsonl')
            first_stage_output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.first_stage.jsonl')

            if 'few-shot' in setting_name:
                work_items.append((input_path, output_path, 'chat' if chat_mode else 'complete', len(dataset)))
            else:
                work_items.append((input_path, first_stage_output_path, 'chat', len(dataset)))

    if not skip_stage_1:
        run_multiple_dataset([item for item in work_items if item[2] == 'complete'])
        run_multiple_dataset([item for item in work_items if item[2] == 'chat'])

    work_items = []
    for dataset_name in dataset_name_list:
        for setting_name in setting_name_list:
            if 'few-shot' in setting_name:
                continue
            dataset = dataset_loader.load_dataset(
                dataset_name, setting_name, dataset_dir,
                prompt_path=raw_prompt_path, max_tokens=2048,
                end_of_example="<END>\n", verbose=True)
            # dataset = dataset[:10]
            input_path = os.path.join(output_dir, "inputs", f"{dataset_name}.{setting_name}.jsonl")
            # dataset = dataset[:10]
            # print(dataset[0]['context'])
            output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.jsonl')
            first_stage_output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.first_stage.jsonl')

            first_stage_results = utils.read_jsonl(first_stage_output_path)
            second_stage_input = dataset_loader.generate_second_stage_input(
                dataset_name, dataset, first_stage_results)
            second_stage_input_path = os.path.join(output_dir, "inputs", f"{dataset_name}.{setting_name}.second_stage.jsonl")
            utils.save_jsonl(second_stage_input, second_stage_input_path)
            work_items.append((second_stage_input_path, output_path, 'chat', len(dataset)))
    if not skip_stage_2:
        openai_api.default_engine = "chatgpt"
        run_multiple_dataset(work_items)

    if not skip_stage_3:
        openai_api.default_engine = "chatgpt"
        wrong_dataset_name_setting_name_list = [
            ("aqua-rat", "few-shot-CoT"),
            ("math", "few-shot"),
            ("math", "few-shot-CoT"),
            ("gaokao-physics", "few-shot-CoT"),
        ]
        for dataset_name, setting_name in wrong_dataset_name_setting_name_list:
            zero_shot_dataset = dataset_loader.load_dataset(
                dataset_name, "zero-shot", dataset_dir,
                prompt_path=raw_prompt_path, max_tokens=2048,
                end_of_example="<END>\n", verbose=True)
            few_shot_output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.jsonl')
            few_shot_second_stage_output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.second_stage.jsonl')
            