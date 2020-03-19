#!/usr/bin/env python3

import yaml
from yaml import Loader
import re
from collections import defaultdict,OrderedDict
from operator import itemgetter
import httplib2
from googleapiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
        'SFTKBot-f11cbc51b794.json', scope)
http = credentials.authorize(httplib2.Http())
discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                'version=v4')
service = discovery.build('sheets', 'v4', http=http,
                          discoveryServiceUrl=discoveryUrl)

spreadsheetId1 = '1yQGULyoGeLZ33cp4atgpsKsl_DPlsBo89GzKsojJ6g8'
spreadsheetId2 = '1p9ajyM9exYRCdArCjbpESa2qNe5cIMjaVxf5NWPJIiM'
tierssheetId = '1tMXpv_vqHgIra70trXLBW3WKUhJiF17g1MtXZpTxaFc'

RESULT_LIMIT = 10
SYNERGY_LIMIT = 16

stances = {
        'Back Turn': 'BT',
        'Coassack Kicks': 'CSK',
        'Crane': 'CRA',
        'Destructive Form': 'DES',
        'Dragon': 'DGN',
        'Drunken Master Walk': 'DRU',
        'Ex Handstand': 'EX HSP',
        'Flamingo': 'FLA',
        'Flea': 'FLE',
        'Flicker': 'FLK',
        'Handstand': 'HSP',
        'Hunting': 'HBS',
        'Panther': 'PAN',
        'Peekaboo': 'PKB',
        'Phoenix Stance': 'AOP',
        'Play Dead': 'PLD',
        'Quick Rise': 'QR',
        'Rain Dance': 'RDS',
        'Snake': 'SNA',
        'Tiger': 'TGR'
        }

def partner(char):
    partners = yaml.load(open('partner.yaml'), Loader=Loader)
    if char in partners:
        return partners[char]
    else:
        return "Character not found: **{0}**".format(char)

def search(char, tags):
    combos = yaml.load(open('combo/{0}.yaml'.format(char)), Loader=Loader)
    results = []
    hidden = ["etype", "estart"]
    etypes = list(set([c.get("etype") for c in combos if "etype" in c]))
    estart_counts = {}
    for et in etypes:
        estart_counts[et] = len([c.get("estart").lower() == et for c in combos if "estart" in c])
    for tag in tags:
        if tag[0] == '/' or tag[0] == '-':
            continue
        elif tag[0] == '+':
            tag = tag[1:]
        tag = tag.lower()
        hidden.append(tag)
    for i, combo in enumerate(combos):
        match = True
        for tag in tags:
            if tag[0] == '/':
                if tag[1:].lower() not in '^{0}$'.format(combo['combo'].lower()):
                    match = False
                    break
            elif tag[0] == '-':
                if tag[1:].lower() in combo['tags']:
                    match = False
                    break
            else:
                if tag[0] == '+':
                    tag = tag[1:]
                tag = tag.lower()
                if tag not in combo['tags']:
                    match = False
                    break
        if match:
            results.append(i)
    if "ender" in tags:
        estart = None
        for t in tags:
            if t.lower() in map(lambda t: t.lower(), etypes):
                estart = t
                break
        if estart is not None:
            results = [r for r in results if combos[r].get("estart").lower() == estart.lower()]
    has_ender = "ender" in tags
    num = len(results)
    if num == 0:
        return 'No results found.', {}
    elif num > RESULT_LIMIT:
        filters = defaultdict(int)
        for i in results:
            for t in combos[i]['tags']:
                if not has_ender and t != "ender":
                    filters[t] += 1
        return 'Too many results ({0}).'.format(num), {'Available filters':
                '\n'.join(['{0}({1})'.format(tag, count) for tag, count in
                    sorted(filters.items(),key=itemgetter(1),reverse=True)
                    if count < num])}
    else:
        message = '{0} results found.\n'.format(num)
        output = OrderedDict()
        min_tags = min([len(combos[i]['tags']) for i in results])
        depth = 1
        while depth < min_tags:
            output.clear()
            for i in results:
                combo = combos[i]
                if not has_ender and "ender" in combo['tags']:
                    continue
                head_tags = combo['tags'][:depth]
                k = ' '.join(head_tags)
                if k not in output:
                    output[k] = ''
                output[k] += '{0}\n'.format(
                        combo_string(combo, hidden + head_tags))
            if len(output) > 1 or len(results) == 1:
                break
            depth += 1
        outmsg = ""
        if not has_ender:
            result_etypes = []
            for r_idx in results:
                combo = combos[r_idx]
                if "etype" not in combo:
                    continue
                etype = combo["etype"]
                if etype not in result_etypes:
                    result_etypes.append(etype)
            if len(result_etypes) > 0:
                outmsg += "**Compatible Enders:**\n"
                for res_et in result_etypes:
                    num_enders = len(list(filter(lambda c: ("estart" in c and c["estart"] == res_et), combos)))
                    outmsg += "From {1}: {0} Enders\n".format(num_enders, res_et)
        return message, output, outmsg

def combo_string(combo, hidden):
    output = '`{0}`'.format(combo['combo'])
    if 'damage' in combo:
        damage = combo['damage']
        output += ' **({0})**'.format(damage)
    if 'comment' in combo:
        output += '\n' + combo['comment']
    tags = combo['tags']
    if len(tags):
        s = ', '.join([t for t in tags if t not in hidden])
        if s != "":
            output += '\n*({0})*'.format(s)
    return output

def synergy(char, section='', partner=''):
    db = yaml.load(open('synergy.yaml'), Loader=Loader)
    if char not in db:
        raise Exception("Character not available: **{0}**".format(char))
    info = db[char]
    output = OrderedDict()
    if section and section != 'x':
        if section not in info:
            return "Key invalid: **{0}**".format(section), {}
        sdata = info[section]
        if partner:
            synergy_subsection(section, sdata, partner, output)
            if not output:
                return "Info not available: **{0}**".format(partner), {}
        else:
            synergy_list(section, sdata, output)
    elif partner:
        for s, sdata in info.items():
            synergy_subsection(s, sdata, partner, output)
    else:
        for s, sdata in info.items():
            synergy_list(s, sdata, output)
    return '', output

def synergy_summary(char, entries):
    summary = char
    if entries and 'value' in entries[0]:
        summary += ' ({0})'.format(entries[0]['value'])
    return summary

def synergy_subsection(section, sdata, partner, output):
    result = ''
    starters = []
    if 'starters' in sdata:
        starters = sdata['starters']
        result += 'Starters:\n```' + '\n'.join(starters) + '```\n'
    if 'content' in sdata and sdata['content']:
        d = OrderedDict(sdata['content'])
        if partner in d:
            entries = [synergy_entry(entry) for entry in d[partner]]
            result += '\n'.join(entries)
    if result:
        header = sdata['header']
        output['{0} [{1}]'.format(header, section)] = result

def synergy_list(section, sdata, output):
    syn_list = ([synergy_summary(partner, entries)
        for partner, entries in sdata['content']]
        if sdata['content'] else ['TODO'])
    if len(syn_list) > SYNERGY_LIMIT:
        syn_list = syn_list[:SYNERGY_LIMIT] + ['...']
    summary = ('\n'.join(syn_list))
    output['{0} [{1}]'.format(sdata['header'], section)] = summary

def synergy_entry(entry):
    output = ''
    if 'combo' in entry:
        if entry['combo']:
            output += '`{0}`'.format(entry['combo'])
        if 'value' in entry:
            output += ' **({0})**'.format(entry['value'])
    elif 'value' in entry:
        output = '{0}'.format(entry['value'])
    return output

def frames(char, move):
    char = char.title()
    if char == 'Chun-Li' or char == 'Chunli':
        char = 'Chun Li'
    elif char == 'Jackx' or char == 'Jack X':
        char = 'Jack-X'
    elif char == 'Mbison' or char == 'M Bison' or char == 'Bison':
        char = 'M. Bison'
    token1 = move.split()[0].lower()
    sheet = None
    if token1 == 'bc' or token1 == 'boost':
        ss = service.spreadsheets().values().get(spreadsheetId=spreadsheetId2,
                range='{0}!A:J'.format(char.title())).execute()
        sheet = ss['values']
        move = ' '.join(move.split()[1:])
    else:
        ss = service.spreadsheets().values().get(spreadsheetId=spreadsheetId1,
                range='{0}!A:N'.format(char.title())).execute()
        sheet = ss['values']
    pmove = parse_move(move, sheet)[0]
    d = OrderedDict()
    command = (sheet[0][1] == 'Command')
    for row in sheet[1:]:
        parse0 = parse_move(row[0], sheet)
        parse1 = parse_move(row[1], sheet) if command else ''
        if pmove in parse0 or pmove in parse1:
            for i in range(len(sheet[0])):
                d[sheet[0][i].strip()] = row[i] or '-'
            break
    return d

def lookup_move(move, sheet):
    if move.title() in stances:
        return stances[move.title()].lower()
    s1 = split_helper(move, r'(mid) or (low)', [1, 2])
    if s1: return '/'.join([lookup_move(opt, sheet) for opt in s1])
    s2 = split_helper(move, r'() or( explosion)', [1, 2])
    if s2: return '/'.join([lookup_move(opt, sheet) for opt in s2])
    move = re.sub(r'round house', r'roundouse', move)
    for row in sheet[1:]:
        pprow = row[0].split('**LC')[0].strip()
        pprow = pprow.split('hit')[0].strip()
        pprow = pprow.lower()
        # if move is found
        if move == pprow:
            parse1 = parse_move(row[1] or row[0], sheet)[0]
            return parse1
        # if move has versions and a version is found
        elif move == pprow[:-3]:
            parse1 = parse_move(row[1] or row[0], sheet)[0]
            parse1 = re.sub(pprow[-2:], pprow[-1:], parse1)
            return parse1
    return move

def parse_move(string, sheet):
    string = string.split('**LC')[0].strip()
    string = string.lower()
    token1 = string.split(' ')[0].title()
    if token1 in stances:
        string = ' '.join([stances[token1].lower()] + string.split()[1:])
    string = re.sub(r',?\s+up to \d+ times', r'', string)
    string = re.sub(r'\s+\(?can be done during .+', r'', string)
    string = re.sub(r' (on )?(connect|hit)', r'', string)
    string = re.sub(r'charge\s+\d+f', r'', string)
    string = re.sub(r'lvl\s*(\d+)', r'lvl\1', string)
    string = re.sub(r'during block(stun)?', r'while blocking', string)
    string = re.sub(r'(mash )?[pk]+ to extend', r'', string)
    string = re.sub(
            r'swift step / explosion', r'swift step or explosion', string)
    string = re.sub(r'slap u silly ex', r'qcf+pp', string)
    string = re.sub(r'stone fists ex', r'qcf+kk', string)
    string = norm_notation(string)
    string = re.sub(r'f,b,f+ex', r'f,b,f+pp', string)
    string = re.sub(r'\s*>\s*', r' ', string)
    # Insert braces to mark move for lookup
    string = re.sub(r'([^/]*) \(?([cd]uring|after|before 1st hit of)'
            '( [lmh][pk]| ex)? ([^/\)]*)( 1st hit)?\)?',
            r'{\4\3} \1',
            string)
    # Parse braces and look up the move
    m = re.search(r'\{([^{}]*)\}', string)
    while m:
        string = '/'.join([
            string[:m.start()] + l + string[m.end():]
            for l in lookup_move(m.group(1), sheet).split('/')])
        m = re.search(r'\{([^{}]*)\}', string)
    string = re.sub(r'[()\-]', r'', string)
    string = re.sub(r'([lmh]?[pk])\s*hold', r'[\1]', string)
    # fix version position
    if string.title() in stances:
        string = stances[string.title()].lower()
        return string
    # genericize versions
    #string = re.sub(r'\+', r'.', string)
    string = re.sub(r'\s+', ' ', string).strip()
    return split_ors(string)

def norm_notation(string):
    string = re.sub(
            r'(.+) during ([0-9\-]+f of )?(forward )?jump', r'j.\1', string)
    string = re.sub(r'(.+) neutral or foward jump', r'j.\1', string)
    string = re.sub(r'(.+) while jumping', r'j.\1', string)
    string = re.sub(r'\(?far([\\/]close)?\)?\s+', r'', string)
    string = re.sub(r'stand(ing)?\s+', r'', string)
    string = re.sub(r'close\s+', r'cl.', string)
    string = re.sub(r'crouch(ing)?\s+', r'd+', string)
    string = re.sub(r'forward jump\s+', r'j.', string)
    string = re.sub(r'jump up\s+', r'nj.', string)
    string = re.sub(r'jump (diagonal )?', r'j.', string)
    string = re.sub(r'st?\.', r'', string)
    string = re.sub(r'cr?\.', r'd+', string)
    string = re.sub(r'ju\.', r'nj.', string)
    string = re.sub(r'(.+) \(?air\)?', r'j.\1', string)
    string = re.sub(r'\(?air\)? (.+)', r'j.\1', string)
    string = re.sub(r',\s', r',', string)
    string = re.sub(r'f,df,d,db,b,ub', r'360', string)
    string = re.sub(r'b,db,d,df,f', r'hcf', string)
    string = re.sub(r'f,df,d,db,b', r'hcb', string)
    string = re.sub(r'd,df,f', r'qcf', string)
    string = re.sub(r'd,db,b', r'qcb', string)
    string = re.sub(r'f,d,df', r'dp', string)
    string = re.sub(r'b,d,db', r'rdp', string)
    string = re.sub(r'bdp', r'rdp', string)
    string = re.sub(r'cd', r'f,n,d,df', string)
    string = re.sub(r'fbf', r'f,b,f', string)
    string = re.sub(r'hcbf', r'hcb,f', string)
    string = re.sub(r'ewgf', r'electric wind god fist', string)
    string = re.sub(
            r'press (([lmhpk])?([pk])) repeatedly', r'\3,\3,\3,\3,\1~', string)
    string = re.sub(r'mash (([lmhpk])?([pk]))', r'\3,\3,\3,\3,\1~', string)
    string = re.sub(r'([lmhpk])?([pk])\*', r'\2,\2,\2,\2,\1\2~', string)
    string = re.sub(r'dd', r'd,d', string)
    string = re.sub(r'd,n,d', r'd,d', string)
    return string

def split_helper(string, regex, groups):
    m = re.search(regex, string)
    if m:
        return sum([split_ors(
            (string[:m.start()] or '') + s +
            (string[m.end():] or ''))
            for s in [m.group(n) for n in groups] if s],[])
    return None

def split_ors(string):
    string = re.sub(r'\s*\+\s*', r'+', string)
    s = split_helper(string, r'(p+)(\\|/| or )(k+)', [1, 3])
    if s: return s
    s = split_helper(string, r'(dp) or (rdp)', [1, 2])
    if s: return s
    s = split_helper(string,
            r'([bdfu,]+) or ([bdfu,]+)( or ([bdfu,]+))?', [1, 2, 4])
    if s: return s
    s = split_helper(string,
            r'((\w+\+)?([lmh]?[pk]+)) (\\|/|or) ((\w+\+)?([lmh]?[pk]+))',
            [1, 5])
    if s: return s
    if '/' in string:
        return string.split('/')
    return [string]

def tiers():
    ss = service.spreadsheets().values().get(
            spreadsheetId=tierssheetId, range='Sheet3!F2:F51').execute()
    codes = [r[0] for r in ss['values']]
    return ('http://www.mmcafe.com/tiermaker/sfxt/index.html?tc=ya0-tr'
            + ''.join(codes[:37]) + '00gy00gy00gy00im00im' + ''.join(codes[37:])
            + '-bk5-naSFXT%20Discord' + '\n'
            + 'https://goo.gl/forms/O6wy2IkeP0ZSn6Ws2')
