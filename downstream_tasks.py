from dgnutils import *
from WikiExtractor import findMatchingBraces, splitParts, options, replaceInternalLinks, dropNested, Extractor, compact, pages_from

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
'(?<=\W)' + \
'\([^()]*\)'+ \
'(?=\W|$)' + \
'(?![^{]*})'
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
	'w',
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
	'ML': 'Medieval Latin',
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

RE_FROM = r"(?: :|,|^)(?: (?:\w|-)+)*(?: [Ff]rom| of| [Aa]ttested| [Dd]erivative| [Pp]robably| [Pp]erhaps)(?: (?:\w|-)+)*,? \*?$"

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

def getHtmlText(html):
	"""Get the html via BS4 and then drop tables"""
	soup = bs4.BeautifulSoup(html, features="lxml")
	removeable_elements = soup.find_all("table", {'class':'metadata'}) + soup.find_all("div", {'class':'noprint'}) + soup.find_all('div', {'class':'NavFrame'})
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

async def get_wikitext_async(wikitexts_list):
	"""
	Parent concurrent to get wikitext
	"""
	results = []
	async with trio.open_nursery() as nursery:
		for idx, wikitexts in enumerate(wikitexts_list):
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

def wikitext_is_excluded(wikitext):
	"""
	Determines if wikitext should be ignored and replaced with '' """
	parts = splitParts(wikitext[2:-2])
	title = parts[0]
	if title in ['LDL', ]:
		return True

	# If there is a 'en-noun' or other tag, ignore these
	if re.match(r'\w{2,3}-(?:verb|noun|adj|adv|decl|conj|proper|infl|adecl|pos|latin|gal)(?:$| .*|-.*|/.*)', title):
		return True

	if title in REQUEST_TEMPLATES or re.match(RE_REQUEST_TEMPLATE, title):
		return True
	return False

def multi_parse_wikitext_sentences(sentences: list, cache_file=None, exclude_connection_forming=False):
	logging.debug('Generating list of used wikitexts...')
	wikitext_replacement_dict = {}
	wikitext_list = set(s[s_i[0]:s_i[1]] for s in sentences for s_i in findMatchingBraces(s)) 

	# Exclude some wikitexts (e.g. LDL, en-noun)
	wikitext_list = set(w for w in wikitext_list if not wikitext_is_excluded(w))

	# Exclude connection forming here (when doing REST lookups) and at end (when replacing them)
	if exclude_connection_forming:
		wikitext_list = set(w for w in wikitext_list if not wikitext_is_connection_forming(w))

	if cache_file:
		logging.debug(f'Using cache file: {cache_file}...')
		try:
			with open(cache_file, 'rb+') as f:
				wikitext_replacement_dict = pickle.load(f)
			wikitext_list -= set(wikitext_replacement_dict.keys())
			logging.debug(f'Found {len(wikitext_replacement_dict.keys())} wikitexts in {cache_file}...')
		except FileNotFoundError as e:
			logging.warning(f'Unable to load from {cache_file} due to {e}. Possibly it doesnt exist and will be written to')

	wikitext_list = list(wikitext_list); len(wikitext_list)

	if len(wikitext_list) == 0:
		logging.debug(f'All wikitext accounted for...')
	else:
		logging.debug(f'There are {len(wikitext_list)} to gather...')

		WIKI_API_URL = 'https://en.wiktionary.org/w/api.php?action=expandtemplates&format=json&prop=wikitext&text=' # 90 chars
		PARAM_LEN_LIMIT = 8202 - len(WIKI_API_URL)
		filler = ":::"
		wikitext_groupings = []

		batch_size = 100
		steps = len(wikitext_list)//batch_size + 1
		logging.info(f'Generating groups of wikitexts for api calls over {steps} steps...')
		for step in range(steps):
			if not step % (max(steps//100,1)): print(f'\rStep {step}', end='')

			next_result_batches = []
			next_result_batches.append(wikitext_list[step*batch_size:(step+1)*batch_size])

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


		batch_size = 500
		steps = len(wikitext_groupings)//batch_size + 1; steps
		logging.info(f'Performing API calls on wikitext_groupings over {steps} steps...')
		for step in range(steps):
			print(f'\rStep {step}/{steps}: ', end='')
			results = trio.run(get_wikitext_async, wikitext_groupings[step*batch_size:(step+1)*batch_size]); results;
			print(f'{len(results)} results')
			wikitext_replacement_dict.update({r[0]: r[1] for r in results})
			if step != steps-1: time.sleep(1)
			if cache_file:
				logging.info('Saving cache file')
				with open(cache_file, 'wb+') as f:
					pickle.dump(wikitext_replacement_dict, f)
		
	logging.info('Replacing wikitext in the sentences...')
	fixed_sentences = []
	for sentence in sentences:
		wikitexts = [sentence[s[0]:s[1]] for s in findMatchingBraces(sentence)]

		# Must replace connection_forming here and at the beginning of the function
		if exclude_connection_forming:
			wikitexts = [w for w in wikitexts if not wikitext_is_connection_forming(w)]

		for wikitext in wikitexts:
			sentence = sentence.replace(wikitext, wikitext_replacement_dict.get(wikitext,''))
		fixed_sentences.append(sentence.replace('()','').strip().replace(': ','').replace('\n* ', '\n '))
#	  pdb.set_trace()
	return fixed_sentences

def test_re_from():
	assert bool(re.search(RE_FROM, " : From "))
	assert bool(re.search(RE_FROM, ", from "))
	assert bool(re.search(RE_FROM, " : Probably from the prefix "))
	assert bool(re.search(RE_FROM, ", probably from the prefix "))
	assert bool(re.search(RE_FROM, " : Borrowed from "))
	assert bool(re.search(RE_FROM, ", borrowed from "))
	assert bool(re.search(RE_FROM, " : Borrowed partially from "))
	assert bool(re.search(RE_FROM, ", borrowed partially from "))
	assert bool(re.search(RE_FROM, " : Compound of "))
	assert bool(re.search(RE_FROM, ", compound of "))
	assert bool(re.search(RE_FROM, " : Perhaps from "))
	assert bool(re.search(RE_FROM, ", perhaps from "))
	assert bool(re.search(RE_FROM, ", noun of action from perfect passive participle "))
	assert bool(re.search(RE_FROM, ", from verb "))
	assert bool(re.search(RE_FROM, ' : 1581, first mention is the derivative '))
	assert bool(re.search(RE_FROM, ' : from *'))
	assert bool(re.search(RE_FROM, ' : Probably '))
	assert bool(re.search(RE_FROM, ' : Probably a non-Indo-European '))
	assert bool(re.search(RE_FROM, ' : First attested in the 13th century as '))
	assert bool(re.search(RE_FROM, ' : Probably '))
	assert bool(re.search(RE_FROM, ' : Probably a non-Indo-European '))
	assert bool(re.search(RE_FROM, ' : From the Roman name, '))
	assert not bool(re.search(RE_FROM, ": Borrowed from"))
	assert not bool(re.search(RE_FROM, ", borrowed from"))
	assert not bool(re.search(RE_FROM, ", + noun of action suffix "))

test_re_from()

RE_COGNATE = r"(?: :|,|^|\.)(?: \w+)*(?: [Cc]ognate(?:s{0,1})| [Cc]ompare| [Ss]ee| [Rr]elated| [Mm]ore at| [Ee]quivalent to)(?: \w+)* "
def test_re_cognate():
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
test_re_cognate()
  
def cognate_str(s):
	return bool(re.search(RE_COGNATE, s)) or s in COGNATE_TEXTS

def from_str(s): 
	return bool(re.search(RE_FROM, s)) or s in SINGLE_PATH_TEXTS

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

	#####################
	### MAIN FUNCTION ###
	#####################
	def process_wikidump(self):
		"""
		Main function for converting the extracted wikidump file into mysql
		"""
		refresh_tables(self.cursor, ['etymologies', 'languages'] if not self.test else [])      
		if self.test:
			logging.debug(f'Inserting languages data due to TEST')
			self.cursor.e('INSERT INTO languages SELECT * FROM etymology_explorer_prod.languages')
			# self.cursor.e('INSERT INTO etymologies SELECT * FROM etymology_explorer_prod.etymologies LIMIT 100')


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
		text = get_wikidump_text(word, filename=self.input_path+self.dump_file_name); text[:50]
		e = Extractor(0, 0, word, text); e
		text = e.transform(text); text
		text = e.wiki2text(text); text
		data = compact(e.clean(text), e.title, e.reconstructed_language); data
		processed_wikidump[word] = data
		return processed_wikidump

	def get_processed_text_from_single_word(self, word):
		processed_wikidump = self.get_processed_wikidump_from_single_word(word)
		en_conns_dl, en_etys_dl, en_pos_dl, en_prons_dl, en_defs_dl, etys_dl = self.create_mysql_data_from_processed_wikiextraction_data(processed_wikidump, log=False)

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
			exclude_connection_forming=True,
		)
		en_etys_dl = [{**z[0], 'wikitext':z[1]} for z in zip(en_etys_dl, parsed_etymologies_except_conns)]

		parsed_etymologies = multi_parse_wikitext_sentences(
			[e['wikitext'] for e in en_etys_dl], 
			cache_file=self.cache_path+'ety.wik' if self.cache_path else None,
			exclude_connection_forming=False,
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
			nodeConnections += self.getNodeConnections(connection)
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
		


	def getNodesFromTemplate(self, templateString, nodeType):
		""" 
		{{inh|gd|sga|ech}} => {word:ech, language:'German', } 
		If this is a descendant, then only provide the main word
		Need to implement: 'w', 'cognate', 'cog', 'doublet', others?
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
			raise CognateError('No connections should be made for cognates')
		else:
			raise Exception('No match!')
			
		if any([n['word'] in ['', '-'] or n['language']=='' for n in nodes]):
			raise EmptyWordOrLanguageError(f'Empty word or language for {templateString}!')
			
		if not nodes:
			raise NoNodesError('No nodes returned')
			
		return nodes

	def getOrCreateIdWithDict(self, word, lang):
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


def getConnectionsForID(cursor, _id):
	sql_stmt = """
	SELECT *
	FROM etymologies e 
	INNER JOIN entry_connections ec ON e._id=ec.etymology_id
	INNER JOIN entry_etymologies ee ON ee.entry_id = ec.entry_id
	WHERE e._id = %s
	"""
	# try:
	entry = cursor.d(sql_stmt, _id)[0]; entry
	wtp = get_wikitext_parts_dict(entry); wtp
	c, missing_parts = get_entry_connections(wtp); c
	nodeConnections = [cj for ci in c for cj in getNodeConnections(ci, cursor)]
	return nodeConnections
	# except:
	# print(f'No connections for _id={_id}')

def getIndexForWordAndLanguage(word, lang, data):
	"""data: a dictionary of entries with the keys being indices"""
	return next(iter(d for d in data if d['word']==word and d['language_name']==lang),{}).get('entry_id', None)

def getConnectionsForIndex(idx, cursor, data):
	"""data: a dictionary of entries with the keys being indices"""
#	  singleNodeConnections = []
# data comes from mysql
	entry = data[idx]; entry
	wtp = get_wikitext_parts_dict(entry); wtp
	c, missing_parts = get_entry_connections(wtp); c
	return [cj for ci in c for cj in getNodeConnections(ci, cursor)]

def getAncestorsForIndex(idx):
	idxs = [idx]
	remaining_loops = 100
	while remaining_loops > 0:
		newConnections = getConnectionsForIndex(idx)
		idxs = []
		max_loops -= 1


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
	typen, *parts = [a for a in all_parts+['']*2 if '=' not in a]
	
	partDict = {}
	for a in [a for a in all_parts if '=' in a[1:-1]]: #don't use it if = is first or last
		item = a.split('=')
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
	

def get_wikidump_text(word, filename='/Users/nish/development/git/wikiextractor/input/enwiktionary-latest-pages-articles.xml'):
	"""
	:param word - the word to search for
	:param filname (optional) - the filename to search in
	Get the text of a particular word from the enwiktionary-latest-pages-articles.xml
	Uses pages_from of WikiExtractor
	"""
	with open(filename, 'r') as f:
		for i, page_data in enumerate(pages_from(f)):
			if i and not i % 100000: print(f'\rEvaluated {i} pages', end='')
			id, revid, title, ns, catSet, page = page_data
			if title == word:
				return ''.join(page)
				break
	logging.error(f'Could not find word: {word}')
	return ''

# }}}
