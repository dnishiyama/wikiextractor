import fileinput
from unidecode import unidecode
from dgnutils import *
from wikiextractor.WikiExtractor import findMatchingBraces, splitParts, options, replaceInternalLinks, dropNested, Extractor, compact, pages_from, keepPage
from io import StringIO

options.write_json = True
options.expand_templates = False
options.keepLists=True
options.keepSections=True
options.acceptedNamespaces = ['w', 'wiktionary', 'wikt', 'reconstruction', 'wikipedia', 'wikispecies', 'rhymes', 'q', 'citations', 'wikisource', 'appendix'] # for internal links

# Updated on 9-25-20

# {{{ WIKTIONARY TEMPLATE PARSING

SINGLE_PATH_TEXTS = [
	' : Earlier ',
	' : Back-formation from ',
	' : Backslang for ',
	' : Via ', # need to handle this differently (and through)
	' : Verbal noun to ',
	' : Short for ',
	' : A reduplication of ',
	' : Deverbal ',
	' : After ',
	' : Coined based on ',
	' : A ',
	' : ',
	' : Morphologically ',
	' : Originally ',
	' : Short form for ',
]
BRANCH_TEXTS = [
	' and ', 
	' + ', 
	' or ',
	', + noun of action suffix '
]
COGNATE_TEXTS = [
	' (compare ', # May be able to ignore and skip these
	'*.Compare ',
	' : Formed after ', # French surjection
]
EQUIVALENT_TEXTS = [
	', ',
]
RESTART_TEXTS = [
	', equivalent to ', # teacher -> teach + er
	'. ',
	'.\nSurface analysis: ',
	'. Alternatively from ',
	', alternatively from ',
]

RE_NON_WIKI_PAREN = r'' + \
r'(?<=\W)' + \
r'\([^()]*\)'+ \
r'(?=\W|$)' + \
r'(?![^{]*})'
RE_NON_WIKI_PAREN = r'(?:(?<=\W)|^)\([^()]*\)(?=\W|$)(?![^{]*})'
RE_UNCLOSED_PAREN = r'\([^\)]*?$' # unclosed paren

# Regex for starting clauses
RE_STARTING_CLAUSE = r"^(?:[^{}\n]+)(?: \[^{}\n]+ ?(?::|;|\.)?)* ?(?::|;|\.) "
def remove_starting_clauses(text):
	return re.sub(RE_STARTING_CLAUSE, '', text)

# Regex for starting clauses
RE_LONE_WIKI = r"{{etyl\|\S+?\|\S+?}}|{{(?:inh|der|bor)\|[^|]+?\|[^|]+?(?:\||\|-)?}}|{{(?:qualifier|circa|glossary|unk)\|[^{}]*?}}"
def remove_lone_wikis(text):
	return re.sub(RE_LONE_WIKI, '__wiki__', text)

RE_BULLET = r"[^ ]*BULLET::::- ?"
RE_CONFER = r"^Cf\.(?= )"
# RE_QUOTES = r"\"(\w+)\"(?![^{]*})"

SINGLE_PATH_TYPES = [
	'inherited', 'inh',
	'derived', 'der', 
	'borrowed', 'bor', 
	'mention', 'm', 
	'link', 'l', 
	'compound', 'com', # This and confix are unusual, may need to not continue on single_path (should never be child)
	'affix','af', 
	'suffix', 'suf',
	'prefix', 'pre',
	'confix',
	# 'w', # So wikipedia won't be kept! 
	'learned borrowing', # rare, used in trapezium
	'he-m', 'he-l', # rare, used in Hebrew like עומר
	'ja-r', # rare for japanese words like もしもし
	'ar-root', # rare for arabic words
	'zh-l', 'zh-m', # rare chinese
]
COGNATE_TYPES = [ # These are the definite cognates, any single path is possible
	'cognate', 'cog',
]
BRANCH_TYPES = [
	#der?  entry_id 56, Papiamentu(lang) para
]
RESTART_TYPES = [
	'doublet',
	
	# Not sure about these next ones
	'compound', 'com', # This and confix are unusual, may need to not continue on single_path (should never be child)
	'affix','af', 
	'suffix', 'suf',
	'prefix', 'pre',
	'confix',
]

# Missing Language dict creation ( )
# missing_languages = []
# for desc, template, conn_type, entry_id in all_connections:
#	  typen, parts, partDict = getTemplateInfo(template)

#	  if typen in ['suffix', 'suf', 'prefix', 'pre', 'confix', 'affix', 'compound', 'com', 'l', 'link', 'm', 'mention']:
#		  if parts[0] not in language_dict:
#			  missing_languages.append(parts[0])
#	  elif typen in ['inh', 'inherited', 'der', 'derived', 'bor', 'borrowed', 'learned borrowing', 'lbor', ]:
#		  if parts[0] not in language_dict:
#			  missing_languages.append(parts[0])
#		  if parts[1] not in language_dict:
#			  missing_languages.append(parts[1])
			
# missing_lang_dict = {}
# for l in list(set(missing_languages)):
#	  language = parseTemplates('{{bor|en|'+l+'|__temp__}}', session=session).replace(' __temp__', '')
#	  missing_lang_dict[l] = language

MISSING_LANG_DICT = {
	'ln': 'Lingala',
	'arh': 'Arhuaco',
	'oto-otm-pro': 'Proto-Otomi',
	'crp-mpp': 'Macau Pidgin Portuguese',
	'kg': 'Kongo',
	'omq-otp-pro': "Proto-Oto-Pamean",
	'ira-mid': 'Middle Iranian',
	'ML': 'Medieval Latin', # TODO: Allow this one to link to normal Latin
	'Medieval Greek': 'Byzantine Greek',
	'aat': 'Arvanitika Albanian',
	'fa-cls': 'Classical Persian',
	'de-AT': 'Austrian German',
	'BE.': 'British English',
	'omq-mxt-pro': "Proto-Mixtec",
	'osc-luc': 'Lucanian',
	'szy': 'Sakizaya',
	'grc-aeo': 'Aeolic Greek',
	'la-med': 'Medieval Latin',
	'als': 'Tosk Albanian',
	'la-ren': 'Renaissance Latin',
	'la-lat': 'Late Latin',
	'frc': 'Cajun French',
	'oto-pro': "Proto-Otomian",
	'mkh-okm-A': 'Angkorian Old Khmer',
	'hbo': 'Biblical Hebrew',
	'os-pro': "Proto-Ossetic",
	'ONF.': 'Old Northern French',
	'hi-mid': 'Middle Hindi',
	'omq-zap-pro': "Proto-Zapotecan",
	'njz': 'Nyishi',
	'mfr': 'Marrithiyel',
	'de-CH': 'Swiss High German',
	'iu': 'Inuktitut',
	'it-oit': 'Old Italian',
	'tl-cls': 'Classical Tagalog',
	'roa-oit': 'Old Italian',
	'tbq-lob-pro': "Proto-Lolo-Burmese",
	'bnt-cmn': "Proto-Bantu",
	'und-xnu': 'Xiongnu',
	'teh': 'Tehuelche',
	'gem-sue': 'Suevic',
	'CF.': 'Canadian French',
	'lng': 'Lombardic',
	'prv': 'Provençal',
	'prs': 'Dari',
	'omq-tel': 'Teposcolula Mixtec',
	'fiu-fin-pro ': "Proto-Finnic",
	'bat-pro': "Proto-Balto-Slavic",
	'fa-ira': 'Iranian Persian',
	'xmn': 'Manichaean Middle Persian',
	'inc-kam': 'Kamarupi Prakrit',
	'xme-old': 'Old Median',
	'VG.': 'Viennese German',
	'AE.': 'American English',
	'gkm': 'Byzantine Greek',
	'sa-neo': 'New Sanskrit',
	'arc-imp': 'Imperial Aramaic',
	'tl-old': 'Old Tagalog',
	'aib': 'Aynu',
	'cop-boh': 'Bohairic Coptic',
	'Late Latin': 'Late Latin',
	'AG.': 'Austrian German',
	'New Latin': 'New Latin',
	'khi-kho-pro': "Proto-Khoe",
	'omq-tri-pro': "Proto-Trique",
	'Medieval Latin': 'Medieval Latin',
	'asa': 'Pare',
	'OIr.': 'Old Iranian',
	'dwu': 'Dhuwal',
	'fiu-pro': "Proto-Uralic",
	'fr-CH': 'Switzerland French',
	'qwm': 'Kipchak',
	'qfa-lic-pro': "Proto-Hlai",
	'fra-aca': 'Acadian French',
	'nan-hok': 'Hokkien',
	'es-MX': 'Mexican Spanish',
	'aln': 'Gheg Albanian',
	'non-oen': 'Old East Norse',
	'nv ': 'Navajo',
	'grc-dor': 'Doric Greek',
	'sxu': 'Upper Saxon',
	'fr-CA': 'Canadian French',
	'xtg': 'Transalpine Gaulish',
	'en-US': 'American English',
	'xsc-pro': "Proto-Scythian",
	'la-new': 'New Latin',
	'LL': 'Late Latin',
	'la-vul': 'Vulgar Latin',
	'nan-hai': 'Hainanese',
	'mkh-okm-P': 'Pre-Angkorian Old Khmer',
	'pt-BR': 'Brazilian Portuguese',
	'omq-zpc-pro': "Proto-Zapotec",
	'omq-cha-pro': "Proto-Chatino",
	'und-idn': 'Idiom Neutral',
	'goh-lng': 'Lombardic',
	'sem-jar': 'Jewish Aramaic',
	'xme-ker': 'Kermanic',
	'sa-ved': 'Vedic Sanskrit',
	'zhx': 'Sinitic',
	'mkh-mmn': 'Middle Mon',
	'bo': 'Tibetan',
	'xln': 'Alanic',
	'omq-teo': 'Teojomulco Chatino',
	'ivb': 'Ibatan',
	'sco-smi': 'Middle Scots',
	'xyt': 'Mayi-Thakurti',
	'non-own': 'Old West Norse',
	'grc-att': 'Attic Greek',
	'Koine': 'Koine Greek',
	'xgn': 'Mongolic',
	'ngf-pro': "Proto-Trans-New Guinea",
	'MIr.': 'Middle Iranian',
	'grc-koi': 'Koine Greek',
	'la-ecc': 'Ecclesiastical Latin',
	'sco-osc': 'Early Scots',
	'fro-pic': 'Picard Old French',
	'xme-mid': 'Middle Median',
	'bzj': 'Belizean Creole',
	'tmr': 'Jewish Babylonian Aramaic',
	'auc': 'Huaorani',
	'ang-nor': 'Northumbrian Old English',
	'es-lun': 'Lunfardo',
	'RL.': 'Renaissance Latin',
	'egy-lat': 'Late Egyptian',
	'LL.': 'Late Latin',
	'VL.': 'Vulgar Latin',
	'NL.': 'New Latin',
	'ML.': 'Medieval Latin',
	'EL.': 'Ecclesiastical Latin',
	'ONF.': 'Old Northern French',
	'xno': 'Anglo-Norman',
	'gmw-pro': 'Proto-West Germanic',
	'trk-cmn': 'Common Turkic',
	'urj-fpr-pro': 'Proto-Finno-Permic',
	'xsc-sak-pro': "Proto-Saka",
	'ltc-lat': 'Late Middle Chinese',
	'non-ogt': 'Old Gutnish',
	'bnt-lal': 'Lala (South Africa)',
	'bdm': 'Buduma',
	 'zlw-slv': 'Slovincian',
	 'zle-oru': 'Old Russian',
	 'emb': 'Embaloh',
	 'bas': 'Basaa',
	 'mfi': 'Wandala',
	 'ser': 'Serrano',
	 'ahr': 'Ahirani',
	 'wrk': 'Garawa',
	 ' az': 'Azerbaijani',
	 'abb': 'Bankon',
	 'de ': 'German',
	 'xsc-skw-pro': "Proto-Saka-Wakhi",
	 'inc-psu': 'Sauraseni Prakrit',
	 'sa ': 'Sanskrit',
	 'qfa-adm-pro': "Proto-Great Andamanese",
}

def parseTemplateByRule(self, templateString):
	""" 
	{{inh|gd|sga|ech}} => "Old Irish ech"
	language_dict: {language_code:language_name}
	returns None if it cannot be parsed
	"""
	max_len = 5
	if '{{' in templateString[2:-2]: return None # Skip ones with nested wikitext
	
	typen, parts, partDict = getTemplateInfo(templateString)
	z = {key:{int(i):'' for i in range(max_len)}
		for key in ['parts', 'words', 'trs', 'parens', 'langcodes', 'langs', 'ts', 'alts', 'texts', 'poses', 'lits']
	}
	for i, part in enumerate(parts):
		z['parts'][i] = part
	
	transliterated_langs = ['grc','ar','uk','cop','el','be','ru','hy','ka','gu','got','sva','sa','kn','xmf','tyv']
	ignore_language = False
	prepend = None
	nodes = []
	nodeType = None #TEMP
	
	self.language_dict['afa'] = 'Afroasiatic'

	if typen == 'eeStart': 
		z['words'][0] = z['parts'][1]
		z['langcodes'][0] = z['parts'][0]

	elif typen in ['inh', 'inherited', 'der', 'derived', 'bor', 'borrowed', 'learned borrowing', 'lbor']: 
		z['words'][0] = z['parts'][2] or z['parts'][3]
		z['langcodes'][0] = z['parts'][1]
		z['alts'][0] = z['parts'][3]
		z['ts'][0] = z['parts'][4]
		
	elif typen in ['l', 'link', 'm', 'mention']: 
		z['words'][0] = z['parts'][1]
		z['langcodes'][0] = z['parts'][0]
		ignore_language = True
		z['alts'][0] = z['parts'][2]
		z['ts'][0] = z['parts'][3]
			
	elif typen in ['cog', 'cognate']:
		z['words'][0] = z['parts'][1]
		z['langcodes'][0] = z['parts'][0]
		z['alts'][0] = z['parts'][2]
		z['ts'][0] = z['parts'][3]

	elif typen in ['com', 'compound', 'affix', 'af']: 
		for i in range(1,len(z['parts'])):
			z['words'][i-1] = z['parts'][i]
			
	elif typen in ['confix']: 
		z['words'][0] = f'{z["parts"][1]}-'
		z['words'][1] = f'-{z["parts"][2]}'

	elif typen in ['suffix', 'suf']: 
		z['words'][0] = z['parts'][1]
		z['words'][1] = f'-{z["parts"][2]}'
		
	elif typen in ['prefix', 'pre']: 
		z['words'][0] = f'{z["parts"][1]}-'
		z['words'][1] = z["parts"][2]
		
	elif typen in ['circumfix']: 
		z['words'][0] = f'{z["parts"][1]}-'
		z['words'][1] = f'{z["parts"][2]}'
		z['words'][2] = f'-{z["parts"][3]}'

#     elif typen in ['he-m', 'he-l'],['ar-root'],['zh-l', 'zh-m'], ['ja-r']: 

	elif typen in ['doublet']: 
		z['words'][0] = z["parts"][1]
		prepend = 'Doublet of '
		
	elif typen in ['ar-root', 'syc-root-entry', 'ja-kanjitab']:
		return None
	
	elif typen in ['etyl']:
		z['langcodes'][0] = z["parts"][0]
	
	elif typen in ['obor']:
		prepend = 'Orthographic borrowing from '
		z['langcodes'][0] = z['parts'][1]
		
	else:
		return 'test'
#         raise Exception(typen, templateString)
		
#     if language_code and language_code[:3] in transliterated_langs:
#         transliterations.append(unidecode(words[0]))
#         and unidecode(word) != word: return

	# Some transliterations (unknown wiki media function)
	
	for k,v in z['words'].items():
		if z['words'][k] in ['-', '']: z['words'][k] = None
			
	if not z['words'][0] and typen in ['inh', 'inherited']: z['words'][0] = '[Term?]'
			
	if not ignore_language:
		z['langs'] = {k:self.language_dict.get(v, None) for k,v in z['langcodes'].items()}
			
	for name,v in partDict.items():
		if name in ['transliteration', 'tr']: z['trs'][0] = v
		elif name in ['gloss', 't']: z['ts'][0] = v
		elif name in ['pos']: z['poses'][0] = v
		elif name in ['lit']: z['lits'][0] = v
		for i in range(max_len):
			for key in ['lit']: 
				if name == f'{key}{i+1}': z['lits'][i] = v
			for key in ['gloss', 't']: 
				if name == f'{key}{i+1}': z['ts'][i] = v
			for key in ['transliteration', 'tr']: 
				if name == f'{key}{i+1}': z['trs'][i] = v
			for key in ['pos']: 
				if name == f'{key}{i+1}': z['poses'][i] = v
		
	# Special cases
	if not z['words'][0] and z['trs'][0]: z['words'][0] = z['trs'][0] 
		
	string = ''
	if prepend: string += prepend
	texts = []

	for i in range(max_len):
		# tr, gloss, pos, lit
		if z['trs'][i]: z['parens'][i] = z['trs'][i]
		if z['ts'][i]: z['parens'][i] += f'{", " if z["parens"][i] else ""}“{z["ts"][i]}”'
		if z['poses'][i]: z['parens'][i] += f'{", " if z["parens"][i] else ""}{z["poses"][i]}'
		if z['lits'][i]: z['parens'][i] += f'{", " if z["parens"][i] else ""}literally “{z["lits"][i]}”'
		
		if z['langs'][i]: z['texts'][i] = z['langs'][i]
		if z['alts'][i]: z['words'][i] = z['alts'][i]
		if z['words'][i]: z['texts'][i] += f' {z["words"][i]}' if z["langs"][i] else z["words"][i]
		if i == 0 and not z['words'][i] and z['words'][i+1] : string += '+ ' # special case for suffix with no first item
		z['texts'][i] += f' ({z["parens"][i]})' if z['parens'][i] else ''
		if z['texts'][i]: texts.append(z['texts'][i])
	string += ' + '.join(texts)

	for k,v in z.items():
		print(f'{k:20}', end=': {')
		for i in range(max_len): print(f'{i}:{v[i] or "None"}, ', end='')
		print('}')
	return string

RE_FROM = r"(?: :|,|^)(?: (?:\w|-|')+)*(?: [Ff]rom| of| [Aa]ttested| [Dd]erivative| [Pp]robably| [Pp]erhaps)(?: (?:\w|-)+)*,? ?\*?$"

WIKI_API_URL = 'https://en.wiktionary.org/w/api.php?action=expandtemplates&format=json&prop=wikitext&text=' # 90 chars
PARAM_LEN_LIMIT = 8202 - len(WIKI_API_URL)
FILLER = ':::'

try:
	templateCache
except:
	templateCache = {}

def parseTemplates(template, session=None, quote=True, cache=False, resetCache=False):
	if cache:
		global templateCache
		if resetCache:
			templateCache = {}
		else:
			if template in templateCache: return templateCache[template]
	
	if not session: session=requests.session()
	html = expandTemplate(template, session=session, quote=quote)
	text = getHtmlText(html)
	linklessText = replaceInternalLinks(text)
	if cache:
		templateCache[template] = linklessText
	return linklessText

def get_sentiment_type(text):
	sentiment = 'other'
	if cognate_str(text): sentiment = 'cognate'
	elif text in BRANCH_TEXTS: sentiment = 'branch'
	elif text in EQUIVALENT_TEXTS: sentiment = 'equivalent'
	elif text in RESTART_TEXTS: sentiment = 'restart'
	elif from_str(text): sentiment = 'from'
	
	return sentiment

def getHtmlText(html):
	"""Get the html via BS4 and then drop tables"""
	soup = bs4.BeautifulSoup(html, features="lxml")
	removeable_elements = soup.find_all("table", {'class':'metadata'})\
		+ soup.find_all("div", {'class':'noprint'})\
		+ soup.find_all('div', {'class':'NavFrame'})\
		+ soup.find_all("table", {'class':'wikitable'})\
		+ soup.find_all("span", {'class':'interProject'})\
		+ soup.find_all("sup")
	for element in removeable_elements: 
		element.decompose()
	text = soup.get_text()
	text = dropNested(text, r'{{', r'}}')
	text = dropNested(text, r'{\|', r'\|}')
	return text.strip()

def expandTemplate(wikitext, session=None, quote=False):
	if quote:
		quote_fn = lambda x: urllib.parse.quote(x)
	else:
		quote_fn = lambda x: x

	quoted_wikitext = quote_fn(wikitext)
	url = WIKI_API_URL + quoted_wikitext

	if len(url) > PARAM_LEN_LIMIT:
		shortened_wikitext = quote_fn(shortenTemplate(wikitext))
		logging.warning(f'Shortening url to {shortened_wikitext} due to it being longer than PARAM_LEN_LIMIT')
		url = WIKI_API_URL + shortened_wikitext

	if not session: session = requests.session()
	resp = session.get(url)
	return resp.json().get('expandtemplates',{}).get('wikitext','')

def clean_word(word): 
	"""Remove all the funky symbols from words so it is good for the database"""
	return word.replace('*', '').replace('“', '"').replace('”', '"').replace('–', '-').replace('‘', '\'').replace('’', '\'').replace('／', ' / ')

def remove_diacritics(word):
	return ''.join(u for u in unicodedata.normalize('NFD', word) if unicodedata.category(u) not in ['Mn'])

def test_remove_diacritics():
	assert remove_diacritics('самизда́т') == 'самиздат'
	assert remove_diacritics('pâr') == 'par'
	assert remove_diacritics('sagēn') == 'sagen'
	assert remove_diacritics('изда́т') == 'издат'

async def get_wikitext_async(wikitexts_to_gather):
	"""
	Parent concurrent to get wikitext
	"""
	results = []
	async with trio.open_nursery() as nursery:
		for idx, wikitexts in  enumerate(wikitexts_to_gather):
			nursery.start_soon(fetch, wikitexts, idx, results) # "1 to total" vs of "0 to total-1"
	return results

async def fetch(wikitexts, idx, results):
	"""
	Child concurrent to get wikitext
	"""
	url = WIKI_API_URL + urllib.parse.quote(FILLER.join(wikitexts))

	if len(wikitexts) == 1 and len(url) > PARAM_LEN_LIMIT:
		url = WIKI_API_URL + urllib.parse.quote(shortenTemplate(wikitexts[0]))
	try:
		resp = await asks.get(url)
		if resp.status_code != 200: 
			raise OverflowError(f'Status code of {resp.status_code} is not 200')
		html = resp.json().get('expandtemplates',{}).get('wikitext','')
		htmls = [h for h in html.split(FILLER)]; htmls
		texts = [getHtmlText(h) for h in htmls]; texts
		linklessTexts = [replaceInternalLinks(t) for t in texts]; linklessTexts
		translated_list = [l.replace('\u200e', '') for l in linklessTexts]; translated_list
		if len(wikitexts) != len(translated_list): 
			raise ArithmeticError()
		results += list(zip(wikitexts, translated_list))
	except OverflowError as o:
		logging.error(f'bad status code {o} at idx: {idx}')
	except ArithmeticError as a:
		logging.error(f'length mismatch {a} at idx: {idx}')
	except Exception as e:
		logging.error(f'error {e} at idx: {idx}')

def shortenTemplate(template):
	parts = splitParts(template[2:-2])
	longest_part = max(range(len(parts)), key=lambda x: len(parts[x])); longest_part
	return makeTemplateFromParts([s for i, s in enumerate(parts) if i != longest_part])

def makeTemplateFromParts(template_parts:list):
	return '{{' + '|'.join(template_parts) + '}}'

def getWikitextsFromString(template_text:str)->list:
	"""Receive a string with wikitext and return the templates"""
	return [template_text[s_i[0]:s_i[1]] for s_i in findMatchingBraces(template_text)]

def wikitext_is_connection_forming(wikitext):
	"""
	Determines if wikitext can be part of a connection. If not then it will likely be replaced with text.
	Currently is based on only the first part (if it is a BRANCH_TYPE, RESTART_TYPE, etc). Other factors might play in eventually
	"""
	parts = splitParts(wikitext[2:-2])
	title = parts[0]
	if title in BRANCH_TYPES + RESTART_TYPES + COGNATE_TYPES + SINGLE_PATH_TYPES:
		return True
	return False

RE_REQUEST_TEMPLATE = r'rf[0-9a-z- ]+'
REQUEST_TEMPLATES = ['MW1913Abbr', 'Nuttall', 'USRegionDisputed', 'Webster 1913', 'ase-rfr', 'attention', 'beer', 'broken ref', 'checksense', 'copyvio suspected', 'delete', 'etystub', 'look', 'merge', 'missing template', 'move', 'split', 'stub entry', 't-needed', 'tbot entry', 'tea room', 'tea room sense', 'ttbc', 'defaults to und', 'unblock']

def wikitext_to_delete(wikitext):
	"""
	Determines if wikitext should be ignored and replaced with '' """
	parts = splitParts(wikitext[2:-2])
	title = parts[0]
	if title in ['LDL', 'wikispecies', 'HE root']:
		return True

	# If there is a 'en-noun' or other tag, ignore these
	if re.match(r'\w{2,3}-(?:verb|noun|adj|adv|decl|conj|proper|infl|adecl|pos|latin|gal)(?:$| .*|-.*|/.*)', title):
		return True

	if title in REQUEST_TEMPLATES or re.match(RE_REQUEST_TEMPLATE, title):
		return True
	return False

def create_wiki_replacement_dict_via_api(wikitext:list, cache_file=None, group_bs=100, call_bs=500):
    logging.debug(f'There are {len(wikitext)} to gather...')

    wikitext_replacement_dict = {}
    WIKI_API_URL = 'https://en.wiktionary.org/w/api.php?action=expandtemplates&format=json&prop=wikitext&text=' # 90 chars
    PARAM_LEN_LIMIT = 8202 - len(WIKI_API_URL)
    filler = ":::"
    wikitext_groupings = []

    steps = len(wikitext)//group_bs + 1
    logging.info(f'Generating groups of wikitexts for api calls over {steps} steps...')
    for step in range(steps):
        if not step % (max(steps//100,1)): print(f'\rStep {step}', end='')

        next_result_batches = []
        next_result_batches.append(wikitext[step*group_bs:(step+1)*group_bs])

        stop = False # for stopping while loop when we cant truncate more
        while not stop and any([len(urllib.parse.quote(filler.join(b))) > PARAM_LEN_LIMIT for b in next_result_batches]):
            replacement_batches = []
            for b in next_result_batches:
                if len(urllib.parse.quote(filler.join(b))) > PARAM_LEN_LIMIT:
                    if len(b) == 1: 
                        stop = True
                        replacement_batches.append(b)
                    else:
                        replacement_batches += [s for s in [b[:len(b)//2]] + [b[len(b)//2:]]]
                else:
                    replacement_batches.append(b)
            next_result_batches = replacement_batches

        wikitext_groupings += next_result_batches

    steps = len(wikitext_groupings)//call_bs + 1; steps
    logging.info(f'Performing API calls on wikitext_groupings over {steps} steps...')
    for step in range(steps):
        print(f'\rStep {step}/{steps}: ', end='')
        results = trio.run(get_wikitext_async, wikitext_groupings[step*call_bs:(step+1)*call_bs])
        print(f'{len(results)} results')
        wikitext_replacement_dict.update({r[0]: r[1] for r in results})
        if step != steps-1: time.sleep(1)
		# logging.info('Replacing wikitext in the sentences...')
    return wikitext_replacement_dict

def load_wikitext_cache_file(cache_file):
	wikitext_replacement_dict = {}
	logging.debug(f'Using cache file: {cache_file}...')
	try:
		with open(cache_file, 'rb+') as f:
			wikitext_replacement_dict = pickle.load(f)
		logging.debug(f'Found {len(wikitext_replacement_dict.keys())} wikitexts in {cache_file}...')
		return wikitext_replacement_dict
	except FileNotFoundError as e:
		logging.warning(f'Unable to load from {cache_file} due to {e}. Possibly it doesnt exist and will be written to')

def save_wikitext_cache_file(cache_file, data):
	logging.debug('Saving cache file')
	with open(cache_file, 'wb+') as f:
		pickle.dump(data, f)

def multi_parse_wikitext_sentences(sentences: list, cache_file=None, ignore_connection_forming=False):
	logging.debug('Generating list of used wikitexts...')
	wikitext_replacement_dict = {}
	# TODO: Could use mwparserfromhell here much easier
	full_wikitext_list = set(s[s_i[0]:s_i[1]] for s in sentences for s_i in findMatchingBraces(s)) 
	# ignore some wikitext since they aren't useful in etymologies (e.g. LDL, en-noun, wikispecies)
	wikitext_list_to_ignore = set(w for w in full_wikitext_list if ignore_connection_forming and wikitext_is_connection_forming(w))
	# Exclude connection forming here (when doing REST lookups) and at end (when replacing them)
	wikitext_list_to_delete = set(w for w in full_wikitext_list if wikitext_to_delete(w) )
	wikitext_list_to_replace = full_wikitext_list - wikitext_list_to_delete - wikitext_list_to_ignore

	# rule_based_wikitext_replacement_dict = 
	# wikitext_replacement_dict.update()
	# create_rule_based_wikitext_replacement_dict(wikitext_list_to_replace)

	# check cache first to allow rule_based to override
	if cache_file: wikitext_replacement_dict.update(load_wikitext_cache_file(cache_file))

	# Let the rule_based_wikitext_replacement_dict override the cached_wikitext_replacement_dict

	wikitext_list_to_gather = list(set(wikitext_list_to_replace) - set(wikitext_replacement_dict.keys())) # must be list for incremental work later

	if len(wikitext_list_to_gather) == 0:
		logging.debug(f'All wikitext accounted for...')
	else:
		logging.debug(f'There are {len(wikitext_list_to_gather)} to gather...')

		new_wikitext_replacement_dict = create_wiki_replacement_dict_via_api(wikitext_list_to_gather)
		wikitext_replacement_dict.update(new_wikitext_replacement_dict)
		if cache_file: save_wikitext_cache_file(cache_file, wikitext_replacement_dict)
		
	logging.info('Replacing wikitext in the sentences...')
	fixed_sentences = []

	for sentence in sentences:
		sentence_wikitext_to_replace = [sentence[s[0]:s[1]] for s in findMatchingBraces(sentence)] 
		for wikitext in sentence_wikitext_to_replace:
			if ignore_connection_forming and wikitext_is_connection_forming(wikitext): 
				continue # ignore some
			elif wikitext_to_delete(wikitext):
				sentence = sentence.replace(wikitext, '')
			else:
				sentence = sentence.replace(wikitext, wikitext_replacement_dict.get(wikitext,''))	
		fixed_sentence = sentence.replace('()','').strip().replace('\n* ', '\n ') # removing - to fix IPA .replace(': ','')
		fixed_sentences.append(fixed_sentence)
	# pdb.set_trace()
	return fixed_sentences

def test_re_from(new_re_from=None):
	global RE_FROM
	if new_re_from: RE_FROM = new_re_from
	good_strings = [" : From ", ", from ", " : Probably from the prefix ", ", probably from the prefix ",
	" : Borrowed from ", ", borrowed from ", " : Borrowed partially from ", ", borrowed partially from ",
	" : Compound of ", ", compound of ", " : Perhaps from ", ", perhaps from ",
	", noun of action from perfect passive participle ", ", from verb ", ' : 1581, first mention is the derivative ',
	' : from *', ' : Probably ', ' : Probably a non-Indo-European ', ' : First attested in the 13th century as ',
	' : Probably ', ' : Probably a non-Indo-European ', ' : From the Roman name, ',  ' : Vṛddhi form of ',
 	' : Apheresized form of ', " : Ren'yokei form of ", " : Ren'yōkei of ", ' : From Late-', ", borrowed from",
	" : From Middle Persian", " : From Neo-", " : From Argentine-", " : From the on'yomi of",
	" : Derived from the masculine form", " : From the on'yomi of"]
	bad_strings = [": Borrowed from", ", + noun of action suffix "]
	for string in good_strings:
		assert from_str(string, new_re_from), f'Should be "from", but is not! {string}'
	for string in bad_strings:
		assert not from_str(string, new_re_from), f'Should not be "from", but is! {string}'

RE_COGNATE = r"(?: :|,|^|\.)(?: \w+)*(?: [Cc]ognate(?:s{0,1})| [Cc]ompare| [Ss]ee| [Rr]elated| [Mm]ore at| [Ee]quivalent to)(?: \w+)* "
def test_re_cognate(new_re_cognate=None):
	global RE_COGNATE
	if new_re_cognate: RE_COGNATE = new_re_cognate
	assert bool(re.search(RE_COGNATE, ". Germanic cognates include "))
	assert bool(re.search(RE_COGNATE, ". Compare "))
	assert bool(re.search(RE_COGNATE, " : Compare "))
	assert bool(re.search(RE_COGNATE, " : compare Greek "))
	assert bool(re.search(RE_COGNATE, ". Cognate with "))
	assert bool(re.search(RE_COGNATE, ". More at "))
	assert bool(re.search(RE_COGNATE, ". Related to "))
	assert bool(re.search(RE_COGNATE, " : Related to "))
	assert bool(re.search(RE_COGNATE, ", related to "))
	assert bool(re.search(RE_COGNATE, " : See "))
	assert bool(re.search(RE_COGNATE, ", see "))
	assert bool(re.search(RE_COGNATE, " : see "))
	assert bool(re.search(RE_COGNATE, " : Possibly cognate with "))
	assert bool(re.search(RE_COGNATE, " : Cognate with "))
	assert bool(re.search(RE_COGNATE, " : Perhaps related to "))
	assert bool(re.search(RE_COGNATE, " : Cognate with standard "))
	assert bool(re.search(RE_COGNATE, " : From a __language__ root cognate with "))
	assert bool(re.search(RE_COGNATE, " : Equivalent to "))
	assert bool(re.search(RE_COGNATE, ' Cognate with '))

def cognate_str(s):
	return bool(re.search(RE_COGNATE, s)) or s in COGNATE_TEXTS

def from_str(s, new_re_from=None, new_single_path_texts=None): 
	global RE_FROM
	global SINGLE_PATH_TEXTS
	if new_re_from: RE_FROM = new_re_from
	if new_single_path_texts: SINGLE_PATH_TEXTS = new_single_path_texts
	decoded_str = unidecode(s)
	return bool(re.search(RE_FROM, decoded_str)) or decoded_str in SINGLE_PATH_TEXTS

def test_from_str():
	assert from_str(' : A ')
	assert from_str(' : Attested in __language__ as ')
	assert from_str(' : ')
	assert from_str(' : From Hiberno-English ')
	assert from_str(' : Hiberno-English and Scottish English pronunciation of ')
	assert from_str(' : Morphologically ')
	assert from_str(' : Originally ')
	assert from_str(' : Perhaps ')
	assert from_str(' : from ')
	assert from_str(' Borrowed from ')

test_from_str()
test_re_cognate()
test_re_from()

def remove_matching_parens(text):
	""" Also remove unmatching parens! """
	wikitext_keys = {}

	# Store the wikitexts as {{0}} to avoid issues with parens inside {{}}
	for i,f in enumerate(reversed(list(findMatchingBraces(text)))):
		replacement_wikitext = '{{'+str(i)+'}}'
		original_wikitext = text[f[0]:f[1]]
		wikitext_keys[replacement_wikitext] = original_wikitext
		text = replacement_wikitext.join(text.rsplit(original_wikitext, 1)) # https://stackoverflow.com/questions/9943504/right-to-left-string-replace-in-python
		# text = text.replace(original_wikitext, replacement_wikitext, 1)

	last_text = text
	count = 0
	while True:
		text = re.sub(RE_NON_WIKI_PAREN, ' ', text)
		text = re.sub(RE_UNCLOSED_PAREN, ' ', text).replace('  ', ' ').strip()
		if last_text == text or count > 100: break
		count += 1
		last_text = text

	# restore the original wikitexts
	for k,v in wikitext_keys.items():
		text = text.replace(k,v)
	return text

def replace_bullets(text): return re.sub(RE_BULLET, '', text)
def replace_cf(text): return re.sub(RE_CONFER, 'Compare', text)
	
def preprocess_etymology(etymology):
	etymology = etymology.replace(u'\xa0', u' ').replace('\n', ' '); etymology
	etymology = replace_bullets(etymology); etymology
	etymology = remove_matching_parens(etymology); etymology
	etymology = remove_lone_wikis(etymology); etymology
	etymology = replace_cf(etymology); etymology
	etymology = remove_starting_clauses(etymology); etymology
	return etymology

def test_all_text_items():
	assert remove_starting_clauses('1670s: variant of ') == 'variant of '
	assert remove_starting_clauses('UK C16. blag blag. Probably from ') == 'Probably from '
	assert remove_starting_clauses('UK C16. blag __language__ blag. Probably from ') == 'Probably from '
	assert remove_starting_clauses('UK C16. Probably from ') == 'Probably from '
	assert remove_starting_clauses('Recorded since 1413; ') == ''
	assert remove_starting_clauses('Echoic; compare Greek ') == 'compare Greek '	
	assert remove_starting_clauses('compare Greek ') == 'compare Greek '	
	assert remove_starting_clauses('variant of ') == 'variant of '	  
	assert remove_starting_clauses('1615-25 ; from ') == 'from '
	assert remove_starting_clauses('From {{inh|ang|gem-pro|*fehu}}. Germanic') == 'From {{inh|ang|gem-pro|*fehu}}. Germanic'
	assert remove_lone_wikis('{{etyl|test|test}} variant of ') == '__wiki__ variant of '
	assert remove_lone_wikis('banana {{etyl|test|test}} variant of ') == 'banana __wiki__ variant of '
	assert remove_lone_wikis('{{inh|test|test|-}} variant of ') == '__wiki__ variant of '
	assert remove_lone_wikis('banana {{inh|test|test|-}} variant of ') == 'banana __wiki__ variant of '
	assert remove_lone_wikis('From {{inh|it|la|Genua}}, possibly from the {{der|it|xlg|-}} word for knee.') == 'From {{inh|it|la|Genua}}, possibly from the __wiki__ word for knee.'
	assert remove_lone_wikis('From {{etyl|NL.|en}} test ') == 'From __wiki__ test '
	assert remove_lone_wikis('{{inh|one|too|many|-}} variant of ') == '{{inh|one|too|many|-}} variant of '
	assert remove_lone_wikis('test {{qualifier|Ikavian}} test') == 'test __wiki__ test'
	assert remove_lone_wikis('test {{circa|1881}} test') == 'test __wiki__ test'
	assert remove_lone_wikis('test {{glossary|adjective}} test') == 'test __wiki__ test'
	assert remove_lone_wikis('test {{unk|en|title=unknown}} test') == 'test __wiki__ test'
	assert remove_lone_wikis('{{bor|hu|de|-}}') == '__wiki__'
	assert remove_lone_wikis('{{inh|hu|de|}}') == '__wiki__'
	assert remove_lone_wikis('{{inh|hu|de}}') == '__wiki__'
	assert remove_lone_wikis('{{inh|hu|de|a}}') == '{{inh|hu|de|a}}'
	assert remove_matching_parens('test') == 'test'
	assert remove_matching_parens('test(test)') == 'test(test)'
	assert remove_matching_parens('test (test)') == 'test'
	assert remove_matching_parens('test (test) test') == 'test test'
	assert remove_matching_parens('(test) test') == 'test' # important for leading dates
	assert remove_matching_parens('test ((test) test (test)) test') == 'test test'
	assert remove_matching_parens('test {{((test) test (test))}} test') == 'test {{((test) test (test))}} test'
	assert remove_matching_parens('wine (possibly {{der|(a wine)}}) {{test}}') == 'wine {{test}}'
	assert remove_matching_parens('Probably {{m|mkh}}, from {{m|mkh}}') == 'Probably {{m|mkh}}, from {{m|mkh}}' # duplicate items is weird
	assert preprocess_etymology('BULLET::::- from {{inh|en|enm|kit}},') == 'from {{inh|en|enm|kit}},'
#	  assert special_replacements('from {{"test"}} test {{test|test}} "test"') == 'from {{"test"}} test {{test|test}} {{eeQuote|test}}'
	assert preprocess_etymology('BULLET::::-Cf. banana') == 'Compare banana'
	assert preprocess_etymology('(1835) super info. from\xa0banana ') == 'from banana'
	assert preprocess_etymology(' : From the Interlingua-English Dictionary.\nFrom ') == 'From'
test_all_text_items()	 

# Regex identifier for parens
# beginning of str or non-word char, positive lookbehind
# open paren followed by no parens, then close paren
# end of str or non-word char, positive lookahead
# not followed by closing } without first a {

RE_FIX_WIKITEXT = r"(?<={{)(_+)(?=\w)" # For removing the extra "_" that are added to avoid duplicate dict keys

class WikiProcessor(object):
	"""
	An extraction task on a article.
	"""
	def __init__(
			self, 
			directory, 
			channel='dev', 
			cache_dir='input/', 
			output_dir='output/', 
			input_dir='input/', 
			dump_file_name='enwiktionary-latest-pages-articles.xml',
			store_intermediates=False,
	):
		"""
		:param channel: The channel of etymology_explorer to run this on. Should usually be dev or test. Options are `test`, `dev`, `staging`, `prod`
		:param cache_dir: caches for the wikitext template expansions
		:param output_dir: location of processed wikidump files
		:param store_intermediates: whether to keep intermediate values, for troubleshooting
		"""
		if cache_dir and cache_dir[-1] != '/': raise Exception('`Cache_dir` must end in `/` if provided')
		if output_dir and output_dir[-1] != '/': raise Exception('`Output_dir` must end in `/` if provided')
		if input_dir and input_dir[-1] != '/': raise Exception('`Input_dir` must end in `/` if provided')
		if directory[-1] != '/': raise Exception('`directory` must end in `/` ')

		self.store_intermediates = store_intermediates
		self.cache_path = directory+cache_dir if cache_dir else None
		self.output_path = directory+output_dir if output_dir else None
		self.input_path = directory+input_dir if input_dir else None
		self.dump_file_name = dump_file_name
		self.channel = channel
		self.test = self.channel == 'test'

		self.wl_2_id = None # dict of values converting (word,lang) into and id
		self.next_wl_2_id = None # Next unused _id 
		self.language_dict = None # dict of languages_used
		self.unmatched_words = [] # list of words that will need to be added

		u = os.environ['RDS_ETY_USER']; p = os.environ['RDS_ETY_PASSWORD']; h = os.environ['RDS_ETY_HOST']
		self.database = f'etymology_explorer_{self.channel}'
		logging.info(f'Using database: {self.database}')
		self.conn, self.cursor = connect(self.database, user=u, password=p, host=h)

	def load_language_dict(self):
		self.language_dict = {s['language_code']:s['language_name'] for s in self.cursor.d('SELECT * FROM languages WHERE key_language=1')};
		self.language_dict.update(MISSING_LANG_DICT)

	def load_wl_2_id_values(self):
		""" Returns wl_2_id, next_wl_2_id, and unmatched_words, all needed for getOrCreateIdWithDict """
		logging.info('Creating wl_2_id dictionary...')
		self.wl_2_id = {(d['word'], d['language_name']): d['_id'] for d in self.cursor.d('SELECT _id, word, language_name FROM etymologies')}; len(self.wl_2_id)
		self.next_wl_2_id = max([*self.wl_2_id.values(), -1]) + 1

	def initialize_db(self):
		""" Clear out the database, except for key tables (etymologies, languages) """
		# from dgnutils. Repair missing tables
		if self.test:
			logging.debug(f'TEST ENVIRONMENT, only keeping languages')
			refresh_tables(self.cursor, exclude=['languages']) # refresh all the tables
			# self.cursor.e('INSERT INTO languages SELECT * FROM etymology_explorer_prod.languages')
			# self.cursor.e('INSERT INTO etymologies SELECT * FROM etymology_explorer_prod.etymologies LIMIT 100')
		else:
			refresh_tables(self.cursor, exclude=['etymologies', 'languages'])      

	def restore_db(self, source_database):
		"""
		Restore the database, based on a source database ('etymology_explorer_prod' or 'etymology_explorer_dev') 
		If self.test (test environment), then just restore `languages` table, otherwise include `etymologies` also
		"""
		if self.test:
			copy_tables(self.cursor, source_database, contents=['languages'])
		else:
			copy_tables(self.cursor, source_database, contents=['etymologies', 'languages'])


	#####################
	### MAIN FUNCTION ###
	#####################
	def process_wikidump(self, commit=True):
		"""
		Main function for converting the extracted wikidump file into mysql
		"""
		self.initialize_db()

		# Initialization of reused dictionaries
		if not self.wl_2_id or not self.next_wl_2_id: self.load_wl_2_id_values()
		if not self.language_dict: self.load_language_dict(); #self.language_dict['qfa-adm-pro']

		# Actual process for processing the wikidump
		processed_wikidump = self.load_wikidump_etymologies() # get word, etymology, def, etc from AA/wiki_00 etc
		en_etys_dl, self.en_dict = self.create_and_insert_mysql_entries(processed_wikidump) # no cache
		wikitext_part_array = self.get_wikitext_part_array(en_etys_dl) # 
		all_connections, missed_etymologies = self.get_connections_from_wikitext_parts(wikitext_part_array)
		node_connections = self.get_nodes_from_connections(all_connections)
		roots, descs, table_sources, entry_numbers = self.get_mysql_data_from_nodes(node_connections)

		self.insert_unmatched_words_into_mysql()
		self.insert_connections_into_mysql(roots, descs, table_sources, entry_numbers)
		# TODO: Make the secondary databases here
		if commit:
			self.conn.commit()

	def get_connections_from_single_wikitext(self, wikitext, store_intermediates=False):
		self.store_intermediates = store_intermediates
		self.load_language_dict()
		logging.warning('Need to add the function to replace non-etymology template')
		wtp = self.get_wikitext_part_array([{'wikitext': wikitext, 'language_name': 'test_language', 'word': 'test_word'}])
		logging.debug(wtp)
		conns, _ = self.get_connections_from_wikitext_parts(wtp); conns
		logging.debug(conns)
		node_conns = self.get_nodes_from_connections(conns); node_conns
		logging.debug(node_conns)
		return node_conns

	def get_processed_wikidump_from_single_word(self, word):
		processed_wikidump = {}
		text = get_wikidump_text(word, filepath=self.input_path + self.dump_file_name); text[:50]
		e = Extractor(0, 0, word, text); e
		text = e.transform(text); text
		text = e.wiki2text(text); text
		data = compact(e.clean(text), e.title, e.reconstructed_language); data
		processed_wikidump[word] = data
		return processed_wikidump

	def get_processed_text_from_single_word(self, word):
		processed_wikidump = self.get_processed_wikidump_from_single_word(word)
		en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl = self.create_mysql_data_from_processed_wikiextraction_data(processed_wikidump, log=True)

		en_prons_dl, en_etys_dl, en_defs_dl = self.parse_wikitext_all(en_prons_dl, en_etys_dl, en_defs_dl)
		return en_prons_dl, en_etys_dl, en_defs_dl

	def load_wikidump_etymologies(self):
		"""
		Get the word, etymology, definitions, etc from the wikiextractor-processed wiktionary articles
		test=True returns about 1000 items
		"""
		processed_wikidump = {}
		# pages = []
		
		letters = [chr(a)+chr(b) for a in range(65,88) for b in range(65,88) ]; letters
		if self.test: letters=['AA']
		logging.info(f'Processing wikiextractor directory {self.output_path}')
		for d in letters:
			logging.debug(f'Processing wikiextractor directory: {d}')
			try:
				for num in [f'{i}{j}' for i in range(10) for j in range(10)]:
					if self.test and num != '00': continue
					path = f'{self.output_path}{d}/wiki_{num}'

					with open(path) as f:
						for entry in f.readlines():
							entry_data = json.loads(entry)

							word = entry_data.get('title', None)
							if not word: raise Exception()

							url = entry_data.get('url', None)
							if not url: raise Exception()

							data = entry_data.get('data', None)

							processed_wikidump[word] = data

	#						  pages += [{'word': word, 'language':k} for k in data.keys()]
			except FileNotFoundError as f:
				logging.info(f'Finished on {d}, {num}. Found {len(processed_wikidump)} words')
				break

		if self.store_intermediates: self.processed_wikidump = processed_wikidump
		return processed_wikidump

	def parse_wikitext_all(self, en_prons_dl, en_etys_dl, en_defs_dl):
		parsed_pronunciations = multi_parse_wikitext_sentences(
			[e['pronunciation'] for e in en_prons_dl], 
			cache_file=self.cache_path+'pron.wik' if self.cache_path else None,
		)
		en_prons_dl = [{**z[0], 'pronunciation':z[1]} for z in zip(en_prons_dl, parsed_pronunciations)]

		parsed_etymologies_except_conns = multi_parse_wikitext_sentences(
			[e['wikitext'] for e in en_etys_dl], 
			cache_file=self.cache_path+'ety.wik' if self.cache_path else None,
			ignore_connection_forming=True,
		)
		en_etys_dl = [{**z[0], 'wikitext':z[1]} for z in zip(en_etys_dl, parsed_etymologies_except_conns)]

		parsed_etymologies = multi_parse_wikitext_sentences(
			[e['wikitext'] for e in en_etys_dl], 
			cache_file=self.cache_path+'ety.wik' if self.cache_path else None,
			ignore_connection_forming=False,
		)
		en_etys_dl = [{**z[0], 'etymology':z[1]} for z in zip(en_etys_dl, parsed_etymologies)]

		parsed_definitions = multi_parse_wikitext_sentences(
			[e['definition'] for e in en_defs_dl], 
			cache_file = self.cache_path + 'def.wik' if self.cache_path else None
		)
		en_defs_dl = [{**z[0], 'definition':z[1]} for z in zip(en_defs_dl, parsed_definitions)] 

		if self.store_intermediates:
			self.en_etys_dl = en_etys_dl
			self.en_prons_dl = en_prons_dl
			self.en_defs_dl = en_defs_dl
		return en_prons_dl, en_etys_dl, en_defs_dl

	def create_and_insert_mysql_entries(self, processed_wikidump):
		""" 
		creates the mysql formatted data from processed wikidump, and removes wikitext
		Returns: the dictionaries needed for later processing
		"""
		
		logging.info(f'Creating mysql data to insert')
		en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl = self.create_mysql_data_from_processed_wikiextraction_data(processed_wikidump, log=False)
		if self.store_intermediates:
			self.en_etys_dl = en_etys_dl
			self.en_pos_dl = en_pos_dl
			self.en_prons_dl = en_prons_dl
			self.en_defs_dl = en_defs_dl
			self.etys_dl = etys_dl


		logging.info(f'Converting wikitext into text...')

		en_prons_dl, en_etys_dl, en_defs_dl = self.parse_wikitext_all(en_prons_dl, en_etys_dl, en_defs_dl)

		logging.info(f'Done converting wikitext into text...')

		logging.debug(f'Generating 2_id dicts for connection making...')
		en_dict = {e['entry_id']:e['entry_number'] for e in en_conns_dl}

		self.insert_mysql_entries(en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl)

		return en_etys_dl, en_dict #en_etys_dl is already stored in self, same with en_dict


	def insert_mysql_entries(self, en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl):
		logging.info(f'Removing empty items...')
		en_defs_dl = [e for e in en_defs_dl if e['definition'] != '']

		logging.info(f'Inserting data into mysql...')

		logging.debug(f'Inserting entry_etymologies into mysql...')
		ety_cols = ['entry_id', 'wikitext', 'etymology'] # need to restrict since more are passed along
		self.cursor.dict_insert([{k:v for k,v in e.items() if k in ety_cols} for e in en_etys_dl], 'entry_etymologies')

		logging.debug(f'Inserting entry_connections into mysql...')
		self.cursor.dict_insert(en_conns_dl, 'entry_connections')

		logging.debug(f'Inserting entry_pos into mysql...')
		self.cursor.dict_insert(en_pos_dl, 'entry_pos')

		logging.debug(f'Inserting entry_definitions into mysql...')
		self.cursor.dict_insert(en_defs_dl, 'entry_definitions')

		logging.debug(f'Inserting entry_pronunciations into mysql...')
		self.cursor.dict_insert(en_prons_dl, 'entry_pronunciations')


	def create_mysql_data_from_processed_wikiextraction_data(self, processed_data, log=False):
		"""Take processed wikiextraction data and convert into data to put into mysql"""
		entry_id = 0
		pos_id = 0
		en_conns_dl = []; #{'etymology_id', 'entry_id', 'entry_number'}
		en_etys_dl = []; #{'entry_id', 'wikitext', 'etymology'}
		en_pos_dl = []; #{'entry_id', 'pos_id', 'pos_name'}
		en_prons_dl = []; #{'entry_id', 'pronunciation'}
		en_defs_dl = []; #{'pos_id', 'definition'}
		etys_dl = []; #{'_id', 'word', 'language_name'}
		#last_id = max([*self.wl_2_id.values(), -1])

		for i, (e_word, e_language_data) in enumerate(processed_data.items()):
		# for i, (e_word, e_language_data) in enumerate(Out[21].items()):

			if log and not i % 50000: print(f'{i} / {len(processed_data)}',end='\r')
			for e_language, e_entries in e_language_data.items():
				if e_language == 'url': continue

				e_id = self.getOrCreateIdWithDict(e_word, e_language)
				etys_dl.append({'_id': e_id, 'word': e_word, 'language_name': e_language})

				entry_number = 1
				for e_entry in e_entries:

					for e_key, e_ety_pos_pron in e_entry.items():
						if not e_ety_pos_pron: continue

						if e_key == 'etymology':
							en_etys_dl.append({ # include extra columns so this can be used in connections
								'_id': e_id,
								'word': e_word,
								'language_name': e_language,
								'entry_id':entry_id, 
								'wikitext': e_ety_pos_pron
							})
						elif e_key == 'pronunciation':
							for e_pron in e_ety_pos_pron:
								en_prons_dl.append({'entry_id':entry_id, 'pronunciation':e_pron})
						else: # pos
							for e_definition in e_ety_pos_pron:
								en_defs_dl.append({'pos_id':pos_id,'definition':e_definition})

							en_pos_dl.append({'entry_id':entry_id, 'pos_id':pos_id, 'pos_name':e_key})
							pos_id += 1

					en_conns_dl.append({'etymology_id':e_id,'entry_id':entry_id,'entry_number':entry_number})
					entry_id += 1
					entry_number += 1	 
		logging.info(f'Found {len(en_conns_dl)} new connections to insert')
		logging.info(f'Found {len(en_etys_dl)} new etymologies to insert')
		logging.info(f'Found {len(en_pos_dl)} new pos to insert')
		logging.info(f'Found {len(en_prons_dl)} new pronunciations to insert')
		logging.info(f'Found {len(en_defs_dl)} new definitions to insert')

		return en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl

	def get_wikitext_part_array(self, en_etys_dl):
		logging.info(f'Gathering wikitext parts for {len(en_etys_dl)} entries...')
		wikitext_part_array = [get_wikitext_parts_dict(entry) for entry in en_etys_dl if entry['wikitext']]
		if self.store_intermediates: self.wikitext_part_array = wikitext_part_array
		return wikitext_part_array

	def get_connections_from_wikitext_parts(self, wikitext_part_array):
		"""
		Gets all_connections from wikitext_part_array
		Returns all_connections, missed_etymologies
		"""
		missed_etymologies = []
		all_connections = []
		for i, wikitext_parts in enumerate(wikitext_part_array):
	#		  if i % 20000 == 0: print(f'\r{i}/{len(wikitext_part_array)}', end='')
			connections, missed_parts = get_entry_connections(wikitext_parts)

			if missed_parts:
				missed_etymologies.append(missed_parts)
			if connections:
				all_connections += connections
	#	  if del_after: del wikitext_part_array

		logging.debug(f'Gathered {len(all_connections)} connections...')
		if self.store_intermediates: self.all_connections = all_connections
		if self.store_intermediates: self.missed_etymologies = missed_etymologies
		return all_connections, missed_etymologies

	def get_nodes_from_connections(self, all_connections):
		logging.info(f'Converting connections into nodes...')
		nodeConnections = []
		for i, connection in enumerate(all_connections):
	#		  if i % 50000 == 0: print(f'\r{i}/{len(all_connections)}', end='')
			try:
				nodeConnections += self.getNodeConnections(connection)
			except KeyError as k:
				print(f'KeyError in getNodeConnections: {k}')
	#	  nodeConnections[2003]
		if self.store_intermediates: self.node_connections = nodeConnections
		return nodeConnections
		# if del_after: del all_connections

	def getNodeConnections(self, connection):
		desc, root, conn_type, entry_id = connection
		try:
			if conn_type == 'cog': raise CognateError
				
			rootNodes = self.getNodesFromTemplate(root, 'root')
			descNodes = self.getNodesFromTemplate(desc, 'desc')
			
			if len(rootNodes) >= 2 and len(descNodes) >= 2:
				raise MultiConnectionError
				
			return [[di, ri, entry_id] for di in descNodes for ri in rootNodes]

		except MultiConnectionError as m:
			print('MultiConnectionError!')
			print(rootNodes)
			print(descNodes)
			return []
		except CognateError as c:
			return []
		except EmptyWordOrLanguageError as e:
			return []
		except NoNodesError as e:
			return []
		except TempError as t:
			return []
				# Testing for branch root experiments
	#		  rTypen, rParts, rPartDict = getTemplateInfo(root)
	#		  dTypen, dParts, dPartDict = getTemplateInfo(desc)
	#		  if dTypen in ['com', 'compound', 'affix', 'af']: 
	#			  r = getNodesFromTemplate(root, 'root', language_dict)
	#			  d = [
	#				  {
	#					  'word': p, 
	#					  'language': language_dict[dPartDict.get(f'lang{i+1}', dParts[0])]
	#				  } for i, p in enumerate(dParts[1:]) if p# and '-' not in p 
	#			  ]
	#			  descWords = [di['word'] for di in d]
	#			  rootWords = [ri['word'] for ri in r]
	#			  descLangs = [di['language'] for di in d]
	#			  rootLangs = [ri['language'] for ri in r]
	#			  print()
	#			  print(descWords, '=>', rootWords)
	#			  print(descLangs, '=>', rootLangs)
	#			  input('a')
	#			  clear_output()
		#			  raise Exception()
		
	def getNodesFromTemplate(self, templateString, nodeType, allow_non_connections=False):
		""" 
		{{inh|gd|sga|ech}} => {word:ech, language:'German', } 
		If this is a descendant, then only provide the main word
		Need to implement: 'cognate', 'cog', 'doublet', others?
		# TODO: Convert this into two functions, one for getting the data about a template (alt, gloss, word, lang, etc), 
		and another for making nodes
		"""
		nodes = []
		typen, parts, partDict = getTemplateInfo(templateString)
		
		if typen == 'eeStart': 
			nodes.append({'word': parts[1], 'language': parts[0]})
			
		elif typen in ['w']:
			nodes.append({'word': [p for p in parts if p][-1], 'language': 'English'})
		
		# (1) language, (2) word
		elif typen in ['inh', 'inherited', 'der', 'derived', 'bor', 'borrowed', 'learned borrowing', 'lbor']: 
			nodes.append({'word': parts[2] or parts[3], 'language': self.language_dict[parts[1]]})
		
		# (0) language, (1) word
		elif typen in ['l', 'link', 'm', 'mention']: 
	#		  if parts[1] == '': #{{m|la||*brabus}} from bravo Galician
			nodes.append({'word': parts[1] or parts[2], 'language': self.language_dict[parts[0]]})
		
		# (0) language, multiple words
		elif typen in ['com', 'compound', 'affix', 'af', 'confix']: 
			if nodeType == 'root':
				nodes += [
					{
						'word': p, 
						'language': self.language_dict[partDict.get(f'lang{i+1}', parts[0])]
					} for i, p in enumerate(parts[1:]) if p 
				]
			elif nodeType == 'desc':
				# May be able to determine which path if the other route has a "-" in it and '-' not in p
				# But only do that for descendants
				raise TempError
		
		# (0) language, (1) root, (2) suffix [not in descendant nodeType]
		elif typen in ['suffix', 'suf']: 
			nodes.append({ 'word': parts[1], 'language': self.language_dict[partDict.get('lang1', parts[0])] })
			if nodeType == 'root':
				nodes.append({ 'word': parts[2], 'language': self.language_dict[partDict.get('lang2', parts[0])] })
		
		# (0) language, (1) prefix [not in descendant nodeType], (2) root 
		elif typen in ['prefix', 'pre']: 
			if nodeType == 'root':
				nodes.append({ 'word': parts[1], 'language': self.language_dict[partDict.get('lang1', parts[0])] })
			nodes.append({ 'word': parts[2], 'language': self.language_dict[partDict.get('lang2', parts[0])] })
		
		# (0) word, language = "Hebrew"
		elif typen in ['he-m', 'he-l']: 
			nodes.append({'word': parts[0], 'language': 'Hebrew'})
		
		# (0) word, language = "Arabic"
		elif typen in ['ar-root']: 
			nodes.append({'word': parts[0], 'language': 'Arabic'})
		
		# (0) word, language = "Chinese"
		elif typen in ['zh-l', 'zh-m']: 
			nodes.append({'word': parts[0], 'language': 'Chinese'})
			
		# (0) word, language = "Japanese"
		elif typen in ['ja-r']: 
			nodes.append({'word': parts[0], 'language': 'Japanese'})

		elif typen in ['cog', 'cognate']:
			if not allow_non_connections:
				raise CognateError('No connections should be made for cognates when allow_non_connections = false')
			else:
				nodes.append({'word': parts[1] or parts[2], 'language': self.language_dict[parts[0]]})

		else:
			raise Exception('No match!')
			
		if any([n['word'] in ['', '-'] or n['language']=='' for n in nodes]):
			raise EmptyWordOrLanguageError(f'Empty word or language for {templateString}!')
			
		if not nodes:
			raise NoNodesError('No nodes returned')
			
		return nodes

	def getOrCreateIdWithDict(self, word, lang):
		# TODO: Check for language switches like "Medieval Latin" -> "Latin"
		unmatched_word = None
		word = clean_word(word) # removes asterisk and other issues
		try:
			_id = self.wl_2_id[(word, lang)]
		except KeyError:
			word = remove_diacritics(word)
			try:
				_id = self.wl_2_id[(word, lang)]
			except KeyError:
				_id = self.next_wl_2_id
				self.wl_2_id[(word, lang)] = self.next_wl_2_id
				self.next_wl_2_id += 1
				self.unmatched_words.append([_id, word, lang])
		return _id

	def get_mysql_data_from_nodes(self, node_connections):
		
		roots = []; descs = []; table_sources = []; entry_numbers = [];
		for i, (desc, root, entry_id) in enumerate(node_connections):
			desc_id = self.getOrCreateIdWithDict(desc['word'], desc['language'])
			root_id = self.getOrCreateIdWithDict(root['word'], root['language'])

			roots.append(root_id)
			descs.append(desc_id)
			table_sources.append(entry_id)
			entry_numbers.append(self.en_dict[entry_id])

		if self.store_intermediates: self.roots = roots
		if self.store_intermediates: self.descs = descs
		if self.store_intermediates: self.table_sources = table_sources
		if self.store_intermediates: self.entry_numbers = entry_numbers
		return roots, descs, table_sources, entry_numbers

	def insert_unmatched_words_into_mysql(self):
		# TODO: Check all these for opportunities to improve word recognition
		if not self.unmatched_words or len(self.unmatched_words) == 0:
			logging.info(f'Found no unmatched words. Returning...')
			return 
		logging.info(f'Found {len(self.unmatched_words)} unmatched words. Inserting...')
		_ids,words,langs = zip(*self.unmatched_words)
		value_dict = {'_id':_ids, 'word':words,'language_name':langs}
		insert(
			self.cursor, 
			'etymologies', 
			many=True,
			**value_dict
		)

	def insert_connections_into_mysql(self, roots, descs, table_sources, entry_numbers):
		logging.info(f'Found {len(roots)} connection_sources. Inserting...')
		# Connection sources 1.5min
		insert(self.cursor, 'connection_sources', many=True, 
			**{'root':roots,'descendant':descs,'table_source':table_sources,'entry_number':entry_numbers})

		# Connection data 1 min
		# make a set for roots, desc
		conn_set = set(zip(roots,descs))
		roots_set = [s[0] for s in conn_set]
		descs_set = [s[1] for s in conn_set]
		logging.info(f'Found {len(roots_set)} connection_sources. Inserting...')
		insert(self.cursor,'connections',ignore=True,many=True, **{'root':roots_set,'descendant':descs_set,})

	def process_single_word(self, word):
		processed_wikidump = {}

		if not self.wl_2_id or not self.next_wl_2_id: self.load_wl_2_id_values()
		if not self.language_dict: self.load_language_dict(); #self.language_dict['qfa-adm-pro']

		# Grab data from the dump (choose which dump)
		logging.info('Searching through dump (can take a minute)...')
		wiki_dump_path = self.input_path + self.dump_file_name
		data = get_data_from_title(word, wiki_dump_path); data

		# convert that data into the objects
		processed_wikidump[word] = data
		self.processed_wikidump = processed_wikidump
		en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl =\
			self.create_mysql_data_from_processed_wikiextraction_data(processed_wikidump, log=False)

		en_prons_dl, en_etys_dl, en_defs_dl = self.parse_wikitext_all(en_prons_dl, en_etys_dl, en_defs_dl)

		self.en_dict = {e['entry_id']:e['entry_number'] for e in en_conns_dl}

		wikitext_part_array = self.get_wikitext_part_array(en_etys_dl) # 
		# Show the objects

		all_connections, missed_etymologies = self.get_connections_from_wikitext_parts(wikitext_part_array)
		node_connections = self.get_nodes_from_connections(all_connections)
		roots, descs, table_sources, entry_numbers = self.get_mysql_data_from_nodes(node_connections)

	def create_etymology_snapshot(self, snapshot_file):
		"""Create a snapshot for testing"""
		training_examples = {}
		for en_ety in self.en_etys_dl:
			training_examples[en_ety['entry_id']] = {'etymology':en_ety['etymology'], 'wikitext':en_ety['wikitext']}
		with open(snapshot_file, 'w') as f:
			f.write(json.dumps(training_examples))

	def create_all_connections_snapshot(self, snapshot_file):
		"""Create a snapshot for testing"""
		training_examples = {}
		for c in self.all_connections:
			# key is entry_id, value is list of '{start}-{end}' for set comparison
			training_examples.setdefault(c[3], []).append(f'{c[0]}-{c[1]}')
		with open(snapshot_file, 'w') as f:
			f.write(json.dumps(training_examples))

	def create_node_connections_snapshot(self, snapshot_file):
		"""Create a snapshot for testing"""
		training_examples = {}
		for c in self.node_connections:
			training_examples.setdefault(c[2], []).append(f'{c[0]["word"]}:{c[0]["language"]}-{c[1]["word"]}{c[1]["language"]}')
		with open(snapshot_file, 'w') as f:
			f.write(json.dumps(training_examples))



### END OF WIKIEXTRACTOR CLASS

def get_wikitext_parts_dict(entry):
	# Create an appended starting etymology
	etymology = preprocess_etymology(entry.get('wikitext', ''))

#	  if etymology == '': raise Exception() # not an issue? https://en.wiktionary.org/wiki/%EB%88%84%EB%A5%B4%EB%8B%A4
	connector = " : "
	starting_wikitext = "{{eeStart|" + entry['language_name'] + "|"+entry['word']+"}}"
	etymology = starting_wikitext + connector + etymology
	
	# initial value
	wikitext_parts_dict={}
	cur=0
	preceding_wikitext = None
	
	for i, (s, e) in enumerate(findMatchingBraces(etymology, 2)):
	#	#pdb.set_trace()
		wikitext = etymology[s:e]
		if wikitext in wikitext_parts_dict:
			wikitext = wikitext[:2] + '_' + wikitext[2:] # Make it a unique item for the dict
			
		wikitext_parts_dict[wikitext] = {
			'entry_id': entry.get('entry_id',None),
			'preceding_text': etymology[cur:s],
			'wikitype': splitParts(re.sub(RE_FIX_WIKITEXT, '', wikitext)[2:-2])[0], # remove _ from type
			'place': i, #order in the etymology
		}
		if preceding_wikitext:
			wikitext_parts_dict[preceding_wikitext]['following_text'] = etymology[cur:s]
			wikitext_parts_dict[preceding_wikitext]['following_wikitext_array'] = [wikitext]
			wikitext_parts_dict[wikitext]['preceding_wikitext_array'] = [preceding_wikitext]
			
		preceding_wikitext = wikitext
		cur=e
#		  print(wikitext_parts_dict)
	return wikitext_parts_dict

item = {'entry_id': 496,'wikitext': 'Probably {{m|mkh-okm|hvat}}, from {{m|mkh-okm|hvat}}','new_connections': 0,'connection_code': '','relative_code': None,'has_errors': 0,'lock_code': 0,'etymology_id': 1564328,'ec.entry_id': 496,'entry_number': 3,'_id': 1564328,'word': 'วัด','language_name': 'Thai','frequencies': None,'common_descendant': '','simple_definition': None}
#assert '{{_m|mkh-okm|hvat}}' in get_wikitext_parts_dict(item) # Must have the _ working<Paste>


def get_entry_connections(wikitext_parts, verbose=False):
	"""
	Takes a wikitext_parts dictionary and returns a list of connections (wikitext1 "child", wikitext2 "root")
	"""
#	  'SINGLE_PATH' # Flag for sign path, ie, there are no plusses yet
	'COGNATE' # Flag for once cognates start showing up
	'BRANCH' # Flag if there was a branch in the etymology
	'RESTART' # Flag for restarting to original index, like from ". Doublet of"
	'EQUIVALENT' # Flag for = ", "
	'SKIP_UNTIL_RESTART' #Ignore this etymology due to cognate or equivalent
	'MODIFY_LONE_LANGUAGE' # For language tags {{etyl}} that need to be treated as text
	
	context = [] # one array for each place [['SINGLE_PATH'], ['BRANCH']]
	connections = []
	missed_parts = []
	no_match_before_connection = False # determine if we need to ignore this word
	
	def has_branch(): return [c for c in context if 'BRANCH' in c]
	def has_cognate(): return [c for c in context if 'COGNATE' in c]
	def has_restart(): return [c for c in context if 'RESTART' in c]
	def log(text): 
		if verbose:
			logging.debug(text)
		else:
			pass
	
	wikitexts = list(wikitext_parts.keys()); wikitexts
	starting_wikitext = next(iter([k for k,v in wikitext_parts.items() if splitParts(k[2:-2])[0]=='eeStart']),None)
	if not starting_wikitext: raise Exception('No starting wikitext')

	for j, wikitext_live in enumerate(wikitexts[1:]): # Skip the first since it is the start
		
		if logging.getLogger().getEffectiveLevel() < 20:
			wikitext = json.loads(json.dumps(wikitext_live)) # To avoid changing the live version for debugging
		else:
			wikitext = wikitext_live
			
		log(f'##### \nEvaluating {j}: {wikitext}\n{wikitext}')
		log(f'##### Info {j}: {wikitext_parts[wikitext]}')
		log(f'##### Context: {context}')
		
		### DATA INITIALIZATION ###
		
		no_match=False # initialize
		missed_parts = []
		
		following_wikitext_array = wikitext_parts[wikitext].get('following_wikitext_array', [])
		preceding_wikitext_array = wikitext_parts[wikitext].get('preceding_wikitext_array', []) # no default
		preceding_text = wikitext_parts[wikitext]['preceding_text'] # no default
		wikitype = wikitext_parts[wikitext]['wikitype']
		place = wikitext_parts[wikitext].get('place', j)
		
		
		# SKIP SINGLE WIKITEXT (THEN CONTINUE)

		# connect the words around this skipped word 
#		  if len(context) > 0 and 'MODIFY_LONE_LANGUAGE' in context[-1] and len(preceding_wikitext_array) != 0:
#			  log(f'### Skipping {i}: {wikitext}')
# #			  And update the text first (depends on the changing preceding_array)
#			  p_pt = wikitext_parts[preceding_wikitext_array[-1]].get('preceding_text', '')
#			  p_pt_c = p_pt + '__language__' + wikitext_parts[wikitext]['preceding_text']
#			  wikitext_parts[wikitext]['preceding_text'] = p_pt_c
#			  preceding_text = p_pt_c
			
# #			  Update the true value, and update the reference (can't do this before now)s
#			  p_pwt = list(set(pi for p in preceding_wikitext_array for pi in wikitext_parts[p].get('preceding_wikitext_array', [])))	   
#			  wikitext_parts[wikitext]['preceding_wikitext_array'] = p_pwt
#			  preceding_wikitext_array = p_pwt


			
		# SKIP UNTIL RESTART
		
			
			
		### EVALUATION OF PATH ###
			
		# Ignoring EQUIVALENT TYPE
#		  elif preceding_text in EQUIVALENT_TEXTS:
#			  log(f'### Ignoring_2 EQUIVALENT_TEXTS {i}: {wikitext}')
#			  for p in preceding_wikitext_array:
#				  for p_p in wikitext_parts[p].get('preceding_wikitext_array',[]):
#					  connections.append([p_p, wikitext, wikitype])
#			  for f in following_wikitext_array:
#				  wikitext_parts[f]['preceding_wikitext_array'] += preceding_wikitext_array
#			  context.append(['EQUIVALENT', 'SINGLE_PATH']) # is equivalent needed?
		
		# special case for "Attested in {language}"
#		  elif wikitype in ['inh']

		# special case for {{unk}} which is unknown # dont do this until I know this tag more
			
		# RESTART
		# start the connections back to the starting word
		
#		  elif wikitype in RESTART_TYPES and preceding_text in RESTART_TEXTS:
#			  log(f'### RESTART TEXTS {i}: {wikitext}')
#			  connections.append([starting_wikitext, wikitext, wikitype])
#			  context.append(['RESTART'])

			
		# BRANCH ( CONTINUE )
		
#		  elif 'BRANCH' in context[-1] and wikitype in BRANCH_TYPES and preceding_text in BRANCH_TEXTS:
#			  log(f'### BRANCH CONTINUATION {i}: {wikitext}')
#			  connections.append([starting_wikitext, wikitext, wikitype])
#			  context.append(['RESTART'])

			
		# COGNATE new
		
		if wikitype in COGNATE_TYPES \
				or (cognate_str(preceding_text) and wikitype in SINGLE_PATH_TYPES):
			log(f'### COGNATE NEW {j}: {wikitext}')
			connections.append([starting_wikitext, wikitext, 'cog'])
			context.append(['COGNATE'])
#			  pdb.set_trace()
			
			
		# COGNATE continue
		
#		  elif has_cognate() and wikitype in COGNATE_TYPES:
#			  log(f'### COGNATE CONTINUE {i}: {wikitext}')
#			  connections.append([starting_wikitext, wikitext, 'cog'])
#			  context.append(['COGNATE'])
			
		
		# Continue single path (or from starting etymology)
		
		elif not has_branch() and not has_cognate() and not has_restart() and wikitype in SINGLE_PATH_TYPES:
			log(f'### Continuing single path for	{j}: {wikitext}')
			
			if from_str(preceding_text): # If it is "... from ..."
				log(f'# single path, SINGLE_PATH_TEXTS {j}: {wikitext}')
				for p in preceding_wikitext_array:
					connections.append([p, wikitext, wikitype])
				context.append(['SINGLE_PATH'])
			
			# SIMPLE BRANCH
			elif preceding_text in BRANCH_TEXTS:
				log(f'# single path, BRANCH_TEXTS {j}: {wikitext}')
				# Create connections to word before branch
				for p in preceding_wikitext_array:
					p_p_wikitext_array = wikitext_parts[p].get('preceding_wikitext_array', [])
					wikitext_parts[wikitext]['preceding_wikitext_array'] = p_p_wikitext_array
					for p_p in p_p_wikitext_array: 
						connections.append([p_p, wikitext, wikitype])
				context.append(['BRANCH'])
				
			else:
				no_match=True
				log(f'# single path, NO MATCH {j}: {wikitext}')
				
			
		else:
			log(f'### NO MATCH {j}: {wikitext}')
			no_match=True
			
			
		### CLOSING ###
		
		if no_match:
			if not connections: 
				no_match_before_connection = True
				missed_parts.append({**wikitext_parts[wikitext], 'wikitext': wikitext})
			entry_id = list(wikitext_parts.values())[0]['entry_id']
			connections = [[*[re.sub(RE_FIX_WIKITEXT, '', ci) for ci in c], entry_id] for c in connections]
			return connections, missed_parts
			
		elif False:
			print(f'no match {j}');print()
			print(context)
			print(wikitext_parts[wikitext]);print()
			print(json.dumps(wikitext_parts, indent=2))
#			  print(wikitext_parts,end='\n\n')

#			  print(f'context: {context}')
#			  print(f'not preceding_wikitext {not preceding_wikitext}')
#			  print(f'SINGLE_PATH in preceding_context {"SINGLE_PATH" in preceding_context}')
#			  print(f'wikitype in SINGLE_PATH_TYPES {wikitype in SINGLE_PATH_TYPES}')
#			  print()
#			  print(wikitext_parts,end='\n\n')
			pdb.set_trace()
#			  raise Exception('No match')

	entry_id = list(wikitext_parts.values())[0]['entry_id']
	connections = [[*[re.sub(RE_FIX_WIKITEXT, '', ci) for ci in c], entry_id] for c in connections]
	return connections, missed_parts


# def getConnectionsForID(cursor, _id):
# 	sql_stmt = """
# 	SELECT *
# 	FROM etymologies e 
# 	INNER JOIN entry_connections ec ON e._id=ec.etymology_id
# 	INNER JOIN entry_etymologies ee ON ee.entry_id = ec.entry_id
# 	WHERE e._id = %s
# 	"""
# 	# try:
# 	entry = cursor.d(sql_stmt, _id)[0]; entry
# 	wtp = get_wikitext_parts_dict(entry); wtp
# 	c, missing_parts = get_entry_connections(wtp); c
# 	nodeConnections = [cj for ci in c for cj in getNodeConnections(ci, cursor)]
# 	return nodeConnections
# 	# except:
# 	# print(f'No connections for _id={_id}')

def getIndexForWordAndLanguage(word, lang, data):
	"""data: a dictionary of entries with the keys being indices"""
	return next(iter(d for d in data if d['word']==word and d['language_name']==lang),{}).get('entry_id', None)

# def getConnectionsForIndex(idx, cursor, data):
# 	"""data: a dictionary of entries with the keys being indices"""
# #	  singleNodeConnections = []
# # data comes from mysql
# 	entry = data[idx]; entry
# 	wtp = get_wikitext_parts_dict(entry); wtp
# 	c, missing_parts = get_entry_connections(wtp); c
# 	return [cj for ci in c for cj in getNodeConnections(ci, cursor)]

# def getAncestorsForIndex(idx, max_loops=100):
# 	idxs = [idx]
# 	while max_loops > 0:
# 		newConnections = getConnectionsForIndex(idx)
# 		idxs = []
# 		max_loops -= 1

def get_tree(conn, _id:int, compression:int=1, details:bool=True, hides:list=[], all_entry_numbers:bool=False):
	""" Returns tree and list of etymologies"""
	
	with conn.cursor(pymysql.cursors.DictCursor) as cursor:
		
		_id = int(_id)
		loop_limit = 15
		tree_items = {}; tree = {} # Must use immutable items
		tree_items[_id] = {}
		tree[_id] = tree_items[_id]
		desc_entry_numbers = {} # Used to keep track of the lowest entry_number for each branch
		all_words = set()
		
		while True:
			search_keys = list(set(tree_items.keys()) - set(all_words))
			logging.debug(f'loop {loop_limit}, search_keys {search_keys}')
			logging.debug(f'tree_items.keys() {set(tree_items.keys())}')
			logging.debug(f'past_searches {all_words}')
			logging.debug(f'search_keys {set(tree_items.keys()) - set(all_words)}')
			if len(search_keys) == 0: break
				
			if (not all_entry_numbers):
				query = f"""\
				SELECT DISTINCT root, descendant,
					CASE 
						WHEN special IS NOT NULL THEN 998
						WHEN entry_number IS NULL THEN 999 
						ELSE entry_number 
					END AS entry_number
				FROM {os.environ['ETY_CON_SRC_TABLE']}
				WHERE descendant IN {print_array(search_keys)} 
				ORDER BY entry_number ASC, descendant DESC
				"""
			else:
				query = f"SELECT root, descendant FROM {os.environ['ETY_CON_TABLE']} WHERE descendant IN {print_array(search_keys)}"
			
			cursor.execute(query)
			data = cursor.fetchall()
			
			# TODO: Add code for specifications here
			logging.debug(f'data: {data}')
			all_words |= set(search_keys) # So it isn't included in the future
			for d in data:
				if not all_entry_numbers and desc_entry_numbers.get(d['descendant'], sys.maxsize) < d['entry_number']:
				# Skip if the entry_number is higher than what is stored, otherwise replace
					continue
				
				if d['root'] not in tree_items:
					if 'entry_number' in d: desc_entry_numbers[d['descendant']] = d['entry_number'] # track entry_numbers
					tree_items[d['root']] = {}
					tree_items[d['descendant']][d['root']] = tree_items[d['root']]
			
			loop_limit -= 1
			if (loop_limit <= 0):break
		
		if (compression > 0):
			ety_to_compress = []; # Store all the compression etymologies
			# print(f'$tree_items array_keys: {tree_items}');
	
			# Now remove etymologies with no entries if there is compression >= 1
			if (compression >= 1):
				compression_query = f"""SELECT DISTINCT e._id FROM etymologies e
									LEFT JOIN entry_connections ec ON e._id=ec.etymology_id
									WHERE ec.entry_id IS NULL AND e._id IN {print_array(list(tree_items.keys()))}
									"""
				cursor.execute(compression_query)
	
				# Add etymology_id where the entry_id was null
				ety_to_compress += [r.get('_id', None) for r in cursor.fetchall()] 
				# print(ety_to_compress)
		
			# Make the actual compression (if compression > 0)
			# Connects the compressable's roots with the compressable's descendants
			compress_items = [] # a list of desc-root connections to compress (root is the compressable word)
			for etc in ety_to_compress:
				for desc, root in tree_items.items():
					if etc in root.keys():
						compress_items.append({'desc': desc, 'root': etc}) 
			
			for ci in compress_items:
				del tree_items[ci['desc']][ci['root']] # Delete the connection to this compressable root
				for k,v in tree_items[ci['root']].items():
					tree_items[ci['desc']][k] = tree_items[k] # Replace connections with the roots of the compressable
				
	return ["tree", get_simple_details(conn, list(all_words)), tree, get_entry_connections(tree)]

def canInt(i):
	try:
		new_int = int(i)
		return True
	except: return False

def getTemplateInfo(templateString):
	all_parts = [s for s in splitParts(templateString[2:-2])]	 
	typen, *parts = [a for a in all_parts if '=' not in a]
	
	partDict = {}
	for a in [a for a in all_parts if re.search('^\w+=',a)]: #don't use it if = is first or last
		item = a.split('=',1)
		partDict[item[0]] = item[1]

	# For adding numbered items into the parts array
	intDict = {k:v for k,v in partDict.items() if canInt(k)}; intDict
	orderedPoses = sorted(int(i) for i in intDict.keys())
	for pos in orderedPoses:
		parts.insert(pos-1, partDict[str(pos)])
	return typen, parts, partDict
	
class EmptyWordOrLanguageError(Exception):pass
class CognateError(Exception):pass
class NoNodesError(Exception):pass
class TempError(Exception):pass
class MultiConnectionError(Exception):pass


def get_simple_details(conn, ids:list):
	with conn.cursor(pymysql.cursors.DictCursor) as cursor:
		sql_stmt = f'SELECT _id, word, language_name, simple_definition FROM etymologies WHERE _id IN {print_array(ids)}'
		cursor.execute(sql_stmt)
		data = cursor.fetchall()
		return {
			'words': { 
				d['_id']: {
					'_id': d['_id'],
					'word': d['word'],
					'language_name': d['language_name'],
					'entries': {
						0: {
							'pos': {
								0: {
									'definitions': [
										d['simple_definition']
									]
								}
							}
						}
					} if d['simple_definition'] else {} 
				}
				for d in data
			}
		}

def get_tree_connections(tree):
	connections = []
	for r, d in tree.items():
		connections += [[r, dk] for dk in d.keys()] 
	return connections
	

def get_wikidump_text(word, filepath='/Users/nish/development/git/wikiextractor/input/enwiktionary-latest-pages-articles.xml'):
	"""
	:param word - the word to search for
	:param filname (optional) - the filepath to search in
	Get the text of a particular word from the enwiktionary-latest-pages-articles.xml
	Uses pages_from of WikiExtractor
	"""
	with open(filepath, 'r') as f:
		for i, page_data in enumerate(pages_from(f)):
			if i and not i % 100000: print(f'\rEvaluated {i} pages', end='')
			id, revid, title, ns, catSet, page = page_data
			if title == word:
				return ''.join(page)
				break
	logging.error(f'Could not find word: {word}')
	return ''

def wikiextract_dump(wiki_dump_path, output_path, limit=None):
	"""
	Convert a wiktionary dump file into a group of extracted files
	output_path = directory to output (will add "AA/wiki_00" onto the path)
	wiki_dump_path = path to the dump file e.g. "input/test.xml"
	"""
	pages = extract_pages(wiki_dump_path, limit=limit)
	output_file_path = output_path + 'AA/wiki_00'
	os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
	with open(output_file_path, 'w') as output_file:
		output_file.write('\n'.join([json.dumps(p) for p in pages]))

def extract_pages(wiki_dump_path, limit=None):
	"""
	Convert a wiktionary dump file into a list of json pages
	Should only be used for the test file
	wiki_dump_path = path to the dump file e.g. "input/test.xml"
	"""
	out = StringIO()
	pages=[]
	with open(wiki_dump_path, 'r') as wiki_dump:
		for page_data in pages_from(wiki_dump):
			id, revid, title, ns, catSet, page = page_data
			if ns in ['0','118']: # articles and reconstructions
				e = Extractor(id, revid, title, page) 
				e.extract(out)
				pages.append(json.loads(out.getvalue().replace('\x00','').strip()))
				out.truncate(0)
			if limit and len(pages) >= limit :
				return pages
	return pages

def get_titles_from_wiki_dump(wiki_dump_path, limit=None):
	"""
	Get the list of titles that are in a wikidump
	"""
	pages=[]
	with open(wiki_dump_path, 'r') as wiki_dump:
		for page_data in pages_from(wiki_dump):
			id, revid, title, ns, catSet, page = page_data
			if ns in ['0','118']: # articles and reconstructions
				pages.append(title)
			if limit and len(pages) >= limit :
				return pages
	return pages


# !ls /gdrive/My\ Drive/Work/EtymologyExplorer/Development/input/test.xml
# wikidump path might be '/gdrive/My Drive/Work/EtymologyExplorer/Development/input/enwiktionary-latest-pages-articles.xml'
def get_page_from_wiki_dump(word, wiki_dump_path):
	"""
	finds a page by title from a wiktionary dump
	Returns the lines between <page> and </page> (inclusive)
	Returns a list of lines
	"""
	current_page = []
	found_title = False
	with open(wiki_dump_path, 'r') as wiki_dump:
		for i,line in enumerate(wiki_dump):
			stripped_line = line.strip()
			if stripped_line == '<page>':
				current_page = []
			elif found_title and stripped_line == '</page>': 
				current_page.append(line)
				return current_page
			elif stripped_line == f'<title>{word}</title>':
				found_title = True
			current_page.append(line)

# input_path = '/gdrive/My Drive/Work/EtymologyExplorer/Development/input/enwiktionary-latest-pages-articles.xml'
def get_data_from_title(title, input_path):
	"""
	Get the WikiExtractor parsed data from one entry in the enwik...xml file
	"""
	# input_path = '/gdrive/My Drive/Work/EtymologyExplorer/Development/test.xml'
	out = StringIO()
	title_page = get_page_from_wiki_dump(title, wiki_dump_path=input_path)
	for page_data in pages_from(title_page):
		id, revid, _title, ns, catSet, page = page_data
		if _title == title:
			e = Extractor(0, 0, title, page) 
			e.extract(out)
			data = json.loads(out.getvalue())['data']; data
			return data

# test_file_path = '/gdrive/My Drive/Work/EtymologyExplorer/Development/input/test.xml'
def append_page_onto_wiki_test(page, test_file_path):
	"""
	take a page (list of lines) from the main wiktionary dump via get_page_from_wiki_dump()
	then append that to the test file (test_file_path)
	For adding new test cases
	"""
	with open(test_file_path, "r+") as file:
		file.seek(0, os.SEEK_END) # Move the pointer to the end of the file
		pos = file.tell() - 1 # skips to the very last character in the file

	  # Find last newline character
		while pos > 0 and file.read(1) != "\n":
			pos -= 1
			file.seek(pos, os.SEEK_SET)

	  # delete all later characters ahead (unless at beginning of file)
		if pos > 0:
			file.seek(pos, os.SEEK_SET)
			file.truncate()
		file.writelines(page + ['</mediawiki>']) # Add the new page


# }}}
