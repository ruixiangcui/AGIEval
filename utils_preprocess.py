# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import os
from scripts.constructions import TaskSchema

def read_json_dirs(path):
    fnames_list = []
    for subdir, dirs, files in os.walk(path):
        for file in files:
            fnames_list.append(os.path.join(subdir, file))
    return fnames_list

def read_jsonl(path):
    with open(path) as fh:
        return [json.loads(line) for line in fh.readlines() if line]

def save_jsonl(lines, directory):
    with open(directory, 'w') as f:
        for line in lines:
            f.write('{}\n'.format(json.dumps(line)))

def lsat_preprosess(args):
    def _preprocess_file(input_dir, output_dir):
        def parse_unicode(s):
            return s.encode('utf-8').decode('utf-8')

        def format_lsat(raw):
            cleaned = []
            for r in raw[0]:
                option_string = "ABCDEFGH"
                option_list = []
                for idx, option in enumerate(r['answers']):
                    option_list.append("(" + option_string[idx] + ")" + parse_unicode(option))
                new_instance = TaskSchema(passage=parse_unicode(r['context']),
                                          question=parse_unicode(r['question']),
                                          options=option_list,
                                          label=option_string[r["label"]])
                cleaned.append(new_instance.to_dict())
            return cleaned

        f_list = read_json_dirs(input_dir)
        for path in f_list:
            formated_data = format_lsat(read_jsonl(path))
            full_dir = output_dir + "/" + path.split("/")[-1] + "l"
            save_jsonl(formated_data, full_dir)
    _preprocess_file(args.data_dir, args.output_dir)