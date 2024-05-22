import unittest
import re
import os
from collections import OrderedDict
from nltk.tokenize import WordPunctTokenizer
from argparse import ArgumentParser
import json

class Token(object):

    def __init__(self, text, start, end):
        self.text = text
        self.start = start
        self.end = end

    def __repr__(self):
        return str( (self.text, self.start, self.end) )

def remove_xml_tags(entity):
    entity = re.sub(r"<ENAMEX TYPE=\"(.+?)\">", "", entity)
    entity = re.sub(r"</ENAMEX>", "", entity)
    return entity

def tokenize(text):
    tokens = []
    tokenizer = WordPunctTokenizer()

    syllables = tokenizer.tokenize(text)
    syllables = [ '"' if s == "``" or s == "''" else s for s in syllables ]

    _pos = 0
    for s in syllables:
        start = text.find(s, _pos)
        end = start + len(s)
        _pos = end
        syl = Token(s, start, end)
        tokens.append(syl)
    return tokens

def depth_level(astring):
    level = 0
    first = True
    first_add_child = True
    OPEN_TAG = 1
    stack = []
    i = 0
    while i < len(astring):
        if astring[i:].startswith("<ENAMEX TYPE="):
            if first:
                level += 1
                first = False
            if len(stack) > 0:
                if first_add_child:
                    level += 1
                    first_add_child = False
            stack.append(OPEN_TAG)
            i += len("<ENAMEX TYPE=")
        elif astring[i:].startswith("</ENAMEX>"):
            stack.pop()
            i += len("</ENAMEX>")
        else:
            i += 1
    return level

def get_entities(line):
    debug = False
    raw = ""
    entities = []

    regex_opentag = re.compile(r"<ENAMEX TYPE=\"(.+?)\">")
    regex_closetag = re.compile(r"</ENAMEX>")
    next_start_pos = 0
    match1 = regex_opentag.search(line, next_start_pos)
    stack = []
    if match1:
        raw += line[0:match1.start()]
        next_start_pos = match1.end()
        stack.append(match1)
    else:
        raw = line

    while len(stack) != 0:
        if debug: print("#Current stack", stack)
        match1 = stack.pop()
        if debug: print("#From next_start_pos {}: {}".format(next_start_pos, line[next_start_pos:]))
        next_closetag1 = regex_closetag.search(line, next_start_pos)
        if not next_closetag1:
            print(line)
            raise ValueError("Close tag not found")
        next_end_pos1 = next_closetag1.start()
        match2 = regex_opentag.search(line, next_start_pos, next_end_pos1)
        if match2:
            raw += line[next_start_pos:match2.start()]
            next_start_pos1 = match2.end()
            next_closetag2 = regex_closetag.search(line, next_start_pos1)
            if not next_closetag2:
                raise ValueError("Close tag not found")
            next_end_pos2 = next_closetag2.start()
            match3 = regex_opentag.search(line, next_start_pos1, next_end_pos2)
            if match3:
                level = 1
                raw += line[next_start_pos1:match3.start()]
                next_start_pos2 = match3.end()
                value = line[next_start_pos2:next_end_pos2]
                _type = match3.group(1)

                entity = OrderedDict()
                entity["type"] = _type
                entity["value"] = value
                entity["start"] = len(raw)
                entity["end"] = entity["start"] + len(value)
                entity["level"] = level
                entities.append(entity)

                if debug: print("#Entity:", value, _type, level)
                raw += value
                next_start_pos = next_closetag2.end()
                stack.append(match1)
                stack.append(match2)
            else:
                value = remove_xml_tags( line[match2.end():next_end_pos2] )
                _type = match2.group(1)
                level = 1 + depth_level( line[match2.end():next_end_pos2] )
                if debug: print("#current: ", raw)
                raw += line[next_start_pos1:next_closetag2.start()]
                if debug: print("->", raw)
                entity = OrderedDict()
                entity["type"] = _type
                entity["value"] = value
                entity["start"] = len(raw) - len(value)
                entity["end"] = len(raw)
                entity["level"] = level
                entities.append(entity)

                if debug: print("#Entity:", value, _type, level)
                next_start_pos = next_closetag2.end()
                stack.append(match1)
                next_match2 = regex_opentag.search(line, next_start_pos)
                next_closetag3 = regex_closetag.search(line, next_start_pos)

                if next_match2:
                    if next_closetag3 and next_match2.start() < next_closetag3.start():
                        if debug: print("Next match2:", line[next_match2.start():])
                        if debug: print("#current: ", raw)
                        raw += line[next_start_pos:next_match2.start()]
                        if debug: print("->", raw)
                        next_start_pos = next_match2.end()
                        stack.append(next_match2)
        else:
            value = remove_xml_tags( line[match1.end():next_closetag1.start()] )
            _type = match1.group(1)
            level = 1 + depth_level( line[match1.end():next_closetag1.start()] )
            if debug: print("#current: ", raw)
            raw += line[next_start_pos:next_closetag1.start()]
            if debug: print("->", raw)
            entity = OrderedDict()
            entity["type"] = _type
            entity["value"] = value
            entity["start"] = len(raw) - len(value)
            entity["end"] = len(raw)
            entity["level"] = level
            entities.append(entity)
            if debug: print("#Entity:", value, _type, level)
            next_start_pos = next_closetag1.end()

            next_match1 = regex_opentag.search(line, next_start_pos)
            next_closetag3 = regex_closetag.search(line, next_start_pos)
            if next_match1:
                if next_closetag3 and next_match1.start() < next_closetag3.start():
                    if debug: print("#Next match1:", line[next_match1.start():])
                    if debug: print("#current: ", raw)
                    raw += line[next_start_pos:next_match1.start()]
                    if debug: print("->", raw)
                    next_start_pos = next_match1.end()
                    stack.append(next_match1)
                else:
                    continue
            else:
                if debug: print("#current: ", raw)
                if debug: print("{} {}".format(next_closetag1.end(), line[next_closetag1.end():]))
                if not re.search(r"</ENAMEX>", line[next_closetag1.end():]):
                    raw += line[next_closetag1.end():]
                    if debug: print("->", raw)

    return raw, entities

def find_syl_index(start, end, syllables):
    start_syl_id = None
    end_syl_id   = None
    for i, syl in enumerate(syllables):
        if syl.start == start:
            start_syl_id = i
        if syl.end == end:
            end_syl_id = i+1

        if i > 0 and syl.start >= start and syllables[i-1].end <= start:
            start_syl_id = i
        if i == 0 and syl.start > start:
            start_syl_id = i

        if i < len(syllables)-1 and syl.end < end and syllables[i+1].start > end:
            end_syl_id = i+1

        if syl.end >= end and syl.start < end:
            end_syl_id = i+1
        if i == len(syllables)-1 and syl.end <= end:
            end_syl_id = i+1

        if i > 0 and syl.start < start and syllables[i-1].end < start:
            start_syl_id = i

        if syl.start < start and syl.end >= end:
            start_syl_id = i
            end_syl_id = i + 1

        if i == 0 and len(syllables) == 1 and syl.start < start and syl.end >= end:
            start_syl_id = i
            end_syl_id = i + 1

        if i == len(syllables)-1 and syl.start < start and syl.end > end:
            start_syl_id = i

        if start_syl_id == None and i > 0 and syl.start > start and syllables[i-1].end <= start:
            start_syl_id = i

        if end_syl_id == None and i < len(syllables)-1 and syl.end < end and syllables[i+1].start >= end:
            end_syl_id = i+1

        if i == len(syllables)-1 and start_syl_id == None and syl.start < start and syl.end < end:
            start_syl_id = i

        if i == 0 and syl.start >= start and syl.end >= end:
            start_syl_id = i

    if start_syl_id == None:
        print("Cannot find start_syl_id '{}' (end={}) in '{}'".format(start, end, syllables))
    if end_syl_id == None:
        print("Cannot find end_syl_id '{}' (start={}) in '{}'".format(end, start, syllables))

    return start_syl_id, end_syl_id

count = 0

def xml2tokens(xml_tagged_sent):
    global count
    raw, entities = get_entities(xml_tagged_sent)
    if re.search(r"ENAMEX", raw):
        print(xml_tagged_sent)
        print(raw)
        count += 1

    tokens = tokenize(raw)
    level1_syl_tags = ["O" for i in range(len(tokens))]
    level2_syl_tags = ["O" for i in range(len(tokens))]
    level3_syl_tags = ["O" for i in range(len(tokens))]

    flag = False
    for entity in entities:
        value = entity["value"]
        start = entity["start"]
        end = entity["end"]
        entity_type = entity["type"]
        start_syl_id, end_syl_id = find_syl_index(start, end, tokens)
        if start_syl_id != None and end_syl_id != None:
            if entity["level"] == 1:
                level1_syl_tags[start_syl_id] = "B-" + entity_type
                for i in range(start_syl_id + 1, end_syl_id):
                    level1_syl_tags[i] = "I-" + entity_type
            elif entity["level"] == 2:
                level2_syl_tags[start_syl_id] = "B-" + entity_type
                for i in range(start_syl_id + 1, end_syl_id):
                    level2_syl_tags[i] = "I-" + entity_type
            else:
                level3_syl_tags[start_syl_id] = "B-" + entity_type
                for i in range(start_syl_id + 1, end_syl_id):
                    level3_syl_tags[i] = "I-" + entity_type
        else:
            print("{},{},\"{}\" in '{}' ({})".format(start,end,value,raw,xml_tagged_sent))
            flag = True
    res = list(zip([ tk.text for tk in tokens], level1_syl_tags, level2_syl_tags, level3_syl_tags))
    return res, flag

# Main function to read from input file and write to output file
def main(input_file, output_file):
    results = []

    # Read sentences from input file
    with open(input_file, 'r', encoding='utf-8') as file:
        sentences = file.readlines()

    for sentence in sentences:
        sentence = sentence.strip()  # Remove leading/trailing whitespace
        if sentence:  # Ensure the sentence is not empty
            tokens, flag = xml2tokens(sentence)
            raw, entities = get_entities(sentence)
            sentence_result = {
                "sentence": raw,
                "tokens_and_tags": tokens
            }
            results.append(sentence_result)

    # Write results to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    input_file = 'merged_train_jan.txt'  # Specify your input file name
    output_file = 'output2.json'  # Specify your output file name
    main(input_file, output_file)




# sent = 'w0 <ENAMEX TYPE="A">w1 <ENAMEX TYPE="B">w2 <ENAMEX TYPE="C">w3</ENAMEX> w4</ENAMEX> w5 <ENAMEX TYPE="D">w6</ENAMEX> w7 w8</ENAMEX> w9'
# sent = ' Tại phiên tòa hôm nay, HĐXX đã chấp nhận giảm nhẹ hình phạt, cho hưởng án treo đối với <ENAMEX TYPE=\"PERSON\">Phù Văn Sơn</ENAMEX>, <ENAMEX TYPE=\"PERSON\">Văn Thanh Tâm</ENAMEX>. Đồng thời, giữ nguyên mức án sơ thẩm của <ENAMEX TYPE=\"ORGANIZATION\">TAND <ENAMEX TYPE=\"LOCATION\">huyện Năm Căn</ENAMEX></ENAMEX> (<ENAMEX TYPE=\"LOCATION\">Cà Mau</ENAMEX>) đối với các bị cáo <ENAMEX TYPE=\"PERSON\">Võ Văn Đảo</ENAMEX>, <ENAMEX TYPE=\"PERSON\">Dương Minh Quang</ENAMEX>, <ENAMEX TYPE=\"PERSON\">Lê Hoàng Hải</ENAMEX>, <ENAMEX TYPE=\"PERSON\">Phù Chí Nguyện</ENAMEX>, <ENAMEX TYPE=\"PERSON\">Lê Văn Kiểm</ENAMEX> và <ENAMEX TYPE=\"PERSON\">Nguyễn Minh Phụng</ENAMEX>.'
# print(sent)
# raw, entities = get_entities(sent)
# print(raw)


# res,flag = xml2tokens(sent)   
# print(res,flag)   