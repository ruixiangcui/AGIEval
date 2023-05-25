# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from src import post_process, utils, dataset_loader
from src import evaluation
import os


if __name__ == "__main__":
    dataset_dir = "data/v1"
    raw_prompt_path = "./data/few_shot_prompts.csv"
    gpt_model = 'davinci-003'
    output_dir = "./outputs/{}".format(gpt_model)
    chat_mode = True

    os.makedirs(os.path.join(output_dir, "inputs"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "outputs"), exist_ok=True)

    # dataset_name_list = ["logiqa-en"]
    dataset_name_list = [
        "aqua-rat",
        "math",
        "logiqa-en", "logiqa-zh",
         "jec-qa-kd", "jec-qa-ca",
        "lsat-ar", "lsat-lr", "lsat-rc",
        "sat-math", "sat-en",
        "sat-en-without-passage",
        "gaokao-chinese",
        "gaokao-english",
        "gaokao-geography", "gaokao-history",
        "gaokao-biology", "gaokao-chemistry", "gaokao-physics",
        "gaokao-mathqa",
        "gaokao-mathcloze",
    ]
    setting_name_list = [
        'zero-shot',
        'zero-shot-CoT',
        'few-shot',
        'few-shot-CoT',
    ]

    sum_list = [0] * len(setting_name_list)

    print("\t" + "\t".join(setting_name_list))

    for dataset_name in dataset_name_list:
        accuracy_list = []
        for setting_id, setting_name in enumerate(setting_name_list):
            dataset = dataset_loader.load_dataset(
                dataset_name, setting_name, dataset_dir,
                prompt_path=raw_prompt_path, max_tokens=2048,
                end_of_example="<END>\n", chat_mode=chat_mode)
            utils.save_jsonl(dataset, os.path.join(output_dir, "inputs", f"{dataset_name}.{setting_name}.jsonl"))
            output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.jsonl')
            first_stage_output_path = os.path.join(
                output_dir, "outputs", f'predict.{gpt_model}.{dataset_name}.{setting_name}.first_stage.jsonl')
            second_stage_input_path = os.path.join(
                output_dir, "inputs", f"{dataset_name}.{setting_name}.second_stage.jsonl")

            if not os.path.exists(output_path):
                # print("dataset {0} setting {1} doesn't have results".format(dataset_name, setting_name))
                accuracy_list.append("0")
                continue

            context_list = [item['context'] for item in dataset]

            result_for_human = dataset_loader.load_dataset_as_result_schema(
                dataset_name, dataset_dir
            )

            output_jsons = utils.read_jsonl(output_path)

            if 'zero-shot' in setting_name:
                first_stage_output_jsons = utils.read_jsonl(first_stage_output_path)
                second_stage_input_jsons = utils.read_jsonl(second_stage_input_path)

            for i in range(len(result_for_human)):
                result_for_human[i].model_input = dataset[i]["context"]
                result_for_human[i].model_output = utils.extract_answer(output_jsons[i])
                result_for_human[i].parse_result = post_process.post_process(dataset_name, setting_name, result_for_human[i].model_output)
                result_for_human[i].is_correct = evaluation.evaluate_single_sample(
                    dataset_name, result_for_human[i].parse_result, result_for_human[i].label)
                if 'zero-shot' in setting_name:
                    result_for_human[i].first_stage_output = utils.extract_answer(first_stage_output_jsons[i])
                    result_for_human[i].second_stage_input = second_stage_input_jsons[i]["context"]

            if 'few-shot' in setting_name:
                correct_format = 0
                for i in range(len(result_for_human)):
                    if post_process.try_parse_few_shot_pattern(
                        result_for_human[i].model_output, dataset_name, setting_name):
                        correct_format += 1
                correct_ratio = correct_format / len(result_for_human)
            correct_numer = len([item for item in result_for_human if item.is_correct])
            accuracy = correct_numer / len(result_for_human)
            accuracy_list.append("{0:.2%}".format(accuracy))
            sum_list[setting_id] += accuracy
        print("\t".join([dataset_name] + accuracy_list))
    average_list = []
    for item in sum_list:
        average_list.append("{0:.2%}".format(item/len(dataset_name_list)))
    print("\t".join(["average"] + average_list))