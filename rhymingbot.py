from __future__ import print_function
import praw
import rbot
import sqlite3
import time
import string
import unicodedata

USERNAME = "rhyming_bot"

SUBREDDIT = "botwatch"
MAXPOSTS = 100

SETRHYMINGPHRASES = ["I need a rhyme for "]
SETPRONUNCIATIONPHRASES = ["How do you pronounce "]
STARTRESPONSE = "Here are words that rhyme with "
ENDRESPONSE = "~BLEEP BLOOP~ I am a bot made by /u/jellyw00t ~BLEEP BLOOP~ \n\n"
ENDCREDITS = "My rhymes are generated using this phonetic dictionary published by Carnegie Mellon: http://bit.ly/28WhK8H"

WAIT = 20

dictionary = dict()
descriptions = dict()

print("Opening database")
sql = sqlite3.connect('rhyming.db')
cur = sql.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS oldposts(ID TEXT)')
sql.commit()

start_time = time.time()
print("Logging into Reddit")
r = rbot.login()
print(r.user)

def login():
    start_time = time.time()
    print("Logging into Reddit")
    r = rbot.login()
    print(r.user)

def handle_ratelimit(func, *args, **kwargs):
    while True:
        try:
            func(*args, **kwargs)
            break
        except praw.errors.RateLimitExceeded as error:
            print('\tSleeping for %d seconds' % error.sleep_time)
            time.sleep(error.sleep_time)

def generate_response(comment):
    word = comment.split(SETRHYMINGPHRASES[0].lower())[1]
    word = word.split(" ", 1)[0]
    word = word.split("\n", 1)[0]
    print("Generating rhymes for " + word)
    build_dictionary()
    rhymes = top_ten_rhymes(word)
    if rhymes == "That word is not in my dictionary":
        return "That word is not in my dictionary"
    if rhymes == "No rhymes found":
        return "No rhymes found"

    response = STARTRESPONSE + "*"+word.upper()+"*" + ": \n\n" + rhymes

    return response

def build_dictionary():
    print("Building Pronunciation Dictionary")
    print("[*", end="")
    counter = 0
    with open('pronouncing_dict.txt') as openfileobject:
        for line in openfileobject:
            counter += 1
            if counter%1000 == 0:
                print("*", end="")

            if not line.startswith(";;;"):
                dictionary[line.split("  ")[0]] = line.split("  ")[1].split('\n')[0]
    print("*]")

    print("Building Phoneme Descriptions")
    print("[*", end="")
    with open('phonemes.txt') as openfileobject:
        for line in openfileobject:
            print("*", end="")
            descriptions[line.split('\t')[0]] = line.split('\t')[1].split('\n')[0]
    print("*]")

def top_ten_rhymes(word):
    all_rhymes = find_rhymes(word)
    if len(all_rhymes) == 0:
        return "No rhymes found"
    if len(all_rhymes) == 1:
        return "That word is not in my dictionary"

    word_phonemes = dictionary[word.upper()].split(" ")
    rhyme_dict = dict()
    for rhyme in all_rhymes:
        rhyme_phonemes = dictionary[rhyme.upper()].split(" ")
        for i in range(1, len(rhyme_phonemes)):
            if len(word_phonemes)-i < 0:
                rhyme_dict[rhyme] = i
                break
            if not rhyme_phonemes[len(rhyme_phonemes)-i] == word_phonemes[len(word_phonemes)-i]:
                rhyme_dict[rhyme] = i
                break

    rhyme_dict["knep aloi"] = -1
    top_ten = list()
    for i in range(0, 9):
        top_ten.append("knep aloi")

    for rhyme in rhyme_dict:
        for word in top_ten:
            if rhyme_dict[rhyme] > rhyme_dict[word]:
                top_ten.remove(word)
                top_ten.append(rhyme)
                break

    counter = 0
    for word in top_ten:
        if word == "knep aloi":
            counter += 1

    for i in range(1, counter):
        top_ten.remove("knep aloi")

    response = ""
    for rhyme in top_ten:
        response += "* "+rhyme+" \n\n"

    return response

def find_rhymes(word):
    try:
        pronunciation = dictionary[word.upper()]
    except Exception as e:
        return ["That word is not in my dictionary"]
    phonemes = list()
    phoneme = ""
    for i in range(0, len(pronunciation)):
        if pronunciation[i] == ' ':
            phonemes.append(phoneme)
            phoneme = ""
        else:
            phoneme += pronunciation[i]
    phonemes.append(phoneme)

    last_syllable = get_last_syllable(phonemes)
    rhymes = list()
    for key in dictionary:
        if dictionary[key].endswith(last_syllable) and not key == word.upper():
            rhymes.append(key)

    return rhymes

def get_last_syllable(phonemes):
    i = 0
    for i in range(len(phonemes)-1, 0, -1):
        phoneme = phonemes[i]
        if phoneme[len(phoneme)-1].isdigit():
            if descriptions[phoneme[:len(phoneme)-1]] == "vowel":
                break
        else:
            if descriptions[phoneme] == "vowel":
                break

    last_syllable = ""
    for x in range(i, len(phonemes)):
        last_syllable += phonemes[x]
        if not x == len(phonemes)-1:
            last_syllable += " "
    return last_syllable

def rhymingbot():
    print("Fetching subreddit " + SUBREDDIT)
    subreddit = r.get_subreddit(SUBREDDIT)
    print("Fetching comments")
    comments = subreddit.get_comments(limit=MAXPOSTS)
    for comment in comments:
        cur.execute('SELECT * FROM oldposts WHERE ID=?', [comment.id])
        if not cur.fetchone():
            try:
                cauthor = comment.author.name
                if cauthor.lower() != USERNAME.lower():
                    cbody = comment.body.lower()
                    cbody = unicodedata.normalize('NFKD', cbody).encode('ascii', 'ignore')
                    cbody = cbody.translate(string.maketrans("",""), string.punctuation)
                    if any(key.lower() in cbody for key in SETRHYMINGPHRASES):
                        print("Replying to " + cauthor + " with rhymes")
                        handle_ratelimit(comment.reply, generate_response(cbody))
                    if any(key.lower() in cbody for key in SETPRONUNCIATIONPHRASES):
                        print("Replying to " + cauthor + " with a pronunciation")
                        word = cbody.split(SETPRONUNCIATIONPHRASES[0].lower())[1]
                        word = word.split(" ", 1)[0]
                        word = word.split(" ", 1)[0]
                        build_dictionary()
                        try:
                            reply = word.upper() + " is pronounced " + dictionary[word.upper()]
                        except Exception as e:
                            reply = "That word is not in my dictionary"
                        handle_ratelimit(comment.reply, reply)
            except AttributeError:
                pass

            cur.execute('INSERT INTO oldposts VALUES(?)', [comment.id])
            sql.commit()


while True:
    rhymingbot()
    time.sleep(WAIT)
    if time.time()-start_time > 2700:
        start_time = time.time()
        login()
