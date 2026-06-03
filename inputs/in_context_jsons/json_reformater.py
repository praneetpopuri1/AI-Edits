#reformating timestamps to be consistent with model prompts and directions
import json

name = "Valkyrae"
def get_seconds(x):
    minutes = int(x)
    seconds = round((x - minutes) * 100)
    return float(minutes * 60 + seconds)

json_file = name +".json"
with open(json_file) as f:
    data = json.load(f)

start_vid = data["parts"][0]["start_sec"]
start_seconds = get_seconds(start_vid)

for part in data["parts"]:
    start = get_seconds(part["start_sec"]) - start_seconds
    end = get_seconds(part["end_sec"]) - start_seconds
    part["start_sec"] = start
    part["end_sec"] = end

with open(name + '_fixed.json', 'w') as f:
    json.dump(data,f, indent=2)






