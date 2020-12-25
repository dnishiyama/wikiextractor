import sys, os, shutil, json
from wikiextractor.downstream_tasks import *
from dgnutils import close_connections, connect

# for interactive python
# wp = WikiProcessor('/Users/nish/development/git/wikiextractor/tests/wikiextractor_test_dir/', store_intermediates=True, channel='test', dump_file_name='test.xml')

tests_dir = os.path.dirname(__file__)
extraction_dir = tests_dir +'/wikiextractor_test_dir/' # input will be a subdir
os.makedirs(os.path.dirname(extraction_dir), exist_ok=True)
dump_file_name = 'test.xml'
test_cache_file = extraction_dir + 'input/test_cache.pkl'

def test_cache_files():
	save_data = {'{{test}}':'best', '{{rest}}':'test'} # Used in test_multi_parse_wikitext_sentences
	save_wikitext_cache_file(test_cache_file, save_data)
	load_data = load_wikitext_cache_file(test_cache_file)
	assert load_data == save_data, 'Data does not match!'

def test_internal_links():
	assert replaceInternalLinks('[[Wikispecies:Pezizaceae|Pezizaceae]]') == 'Pezizaceae'
	assert replaceInternalLinks('[[Wikispecies]]') == 'Wikispecies'
	assert replaceInternalLinks('[[Wikispecies:test1|test2]]') == 'test2'
	assert replaceInternalLinks('[[Wikispecies:test1|test2]]ing') == 'test2ing'
	# replaceInternalLinks('[[Wikispecies:test|]]') = 'test' # Should piping trick work?

details = {'user': os.environ['RDS_ETY_USER'], 'password': os.environ['RDS_ETY_PASSWORD'], 'host': os.environ['RDS_ETY_HOST']}
test_conn, test_cursor = connect('etymology_explorer_test', **details)
close_connections(test_cursor, 'etymology_explorer_test')


def test_wikitext_parsing():
	test_cases=[
		['{{wikispecies|test|banana}}', ''],
		['{{IPA|en|/ˈdɪkʃ(ə)n(ə)ɹi/}}', 'IPA: /ˈdɪkʃ(ə)n(ə)ɹi/'],
	]; 
	cache_file=None 
	ignore_connection_forming=False
	wikitext_replacement_dict = create_wiki_replacement_dict_via_api([t[0] for t in test_cases])
	results = [wikitext_replacement_dict[t[0]] for t in test_cases]
	for (test_case, true_result), result in zip(test_cases, results):
		assert true_result == result, f'Error on {test_case}'

def test_multi_parse_wikitext_sentences():
	# test_cache_file = extraction_dir + 'input/test_cache.pkl'
	test_cases_not_real_cases=[ # Must match test_cache_files(), save_data = {'{{test}}':'best', '{{rest}}':'test'}
		['Test {{wikispecies|test|banana}}', 'Test'],
		['{{IPA|en|/ˈdɪkʃ(ə)n(ə)ɹi/}}', 'IPA: /ˈdɪkʃ(ə)n(ə)ɹi/'],
		['{{test}}', 'best'],
		['{{rest}}', 'test'],
		['{{inh|en|enm|test}}', '{{inh|en|enm|test}}'],
	]; 
	results = multi_parse_wikitext_sentences(
		[t[0] for t in test_cases_not_real_cases], 
		cache_file=test_cache_file, 
		ignore_connection_forming=True
	)
	for (test_case, test_case_result), result in zip(test_cases_not_real_cases, results):
		assert test_case_result == result, f'Error on {test_case}'

def test_wiki_extract_dump():
	limit = 5
	dump_file_path = extraction_dir + 'input/test.xml'
	pages = extract_pages(dump_file_path, limit=limit); pages
	assert len(pages) == limit

	assert get_titles_from_wiki_dump(dump_file_path, limit = 5) == ['dictionary', 'free', 'thesaurus', 'encyclopedia', 'portmanteau']

	assert '==English==' in get_wikidump_text('loach', dump_file_path)
	# wiki_dump_path = '/gdrive/My Drive/Work/EtymologyExplorer/Development/input/test.xml'
	# wiki_output_path = '/gdrive/My Drive/Work/EtymologyExplorer/Development/output/'
	# wikiextract_dump(wiki_dump_path, wiki_output_path, limit = 5)    

def test_dump_management():
	"""
	Deletes any output in test extraction_dir (which contains input and output)
	Then tries to convert a xml dump into a list of json objects
	"""
	dump_file_path = extraction_dir + 'input/test.xml'
	output_dir = extraction_dir + 'output/'
	limit = 5

	pages = extract_pages(dump_file_path, limit=limit)
	assert pages[0]['title'] == 'dictionary', 'Did not ignore ns of non 0 or 118'
	try:
		print(f'Trying to delete existing {output_dir}')
		shutil.rmtree(output_dir)
	except Exception as e:
		print('No output to remove')
	wikiextract_dump(dump_file_path, output_dir, limit = None)
	with open(output_dir + 'AA/wiki_00', 'r') as f:
		page_data = [json.loads(l) for l in f.readlines()] 
		# assert len(page_data) == limit
		assert type(page_data[0]) == dict

	# See if we can get the lines of text for the page 'dictionary' from the test dump
	page = get_page_from_wiki_dump('dictionary', dump_file_path)
	assert page[0].strip() == '<page>'
	assert page[1].strip() == '<title>dictionary</title>'

	# see if we can get the extracted data for the 'dictionary' page from the test dump
	data = get_data_from_title('dictionary', dump_file_path)
	assert data['English'][-1]['etymology'][30:50] == 'from {{bor|en|ML.|di'

	# Verify that adding a page to the test dump works
	# Create a duplicated test dump, then add the 'dictionary' page again, then chekc if it appears twice
	# dump_file_path = extraction_dir + 'input/test.xml'
	dump_duplicate_file_path = extraction_dir + 'input/test_duplicate.xml'
	shutil.copy(dump_file_path, dump_duplicate_file_path)
	append_page_onto_wiki_test(page, dump_duplicate_file_path)
	with open(dump_duplicate_file_path, 'r') as f:
		dictionary_count = [r.strip() for r in f.readlines()].count('<title>dictionary</title>')
		assert dictionary_count == 2

def test_single_wiki_process():
	single_wp = WikiProcessor(extraction_dir, store_intermediates=True, cache_dir=None, dump_file_name=dump_file_name, channel='test')
	copy_tables(single_wp.cursor, 'etymology_explorer_dev', 'etymology_explorer_test', contents=['languages'])
	single_wp.process_single_word('loach')
	assert single_wp.node_connections[-1][0]['word'] == 'loach'
	assert single_wp.all_connections[-1][1]  == '{{l|en|LOH|gloss=loach}}'


# WikiProcessor for all downstream activity
wp = WikiProcessor(extraction_dir, store_intermediates=True, cache_dir=None, dump_file_name=dump_file_name, channel='test')
def test_wiki_process():
	"""
	Test the wp.process_wikidump()
	"""
	print(f'\nstoring temporary files in {extraction_dir}')
	assert wp.test == True
	# assert wp.wl_2_id == None
	# assert wp.next_wl_2_id == None

	# test runs should reset the entire database
	# wp.load_wl_2_id_values()
	# assert len(wp.wl_2_id) > 0
	# assert len(wp.wl_2_id) == wp.next_wl_2_id

	# assert wp.language_dict == None
	# wp.load_language_dict()
	# assert len(wp.language_dict) > 0

	# need to reset the wl_2_id since we loaded the word before
	wp.wl_2_id = None
	wp.next_wl_2_id = None
	wp.process_wikidump(commit=False)
	assert wp.channel == 'test'
	assert wp.database == 'etymology_explorer_test'
	# assert len(wp.all_connections)  27
	assert wp.all_connections[0][0] == '{{eeStart|English|dictionary}}'
	# assert len(wp.roots) == 23
	# assert len(wp.descs) == 23
	assert not set([ 'dictionary', 'free', 'thesaurus', 'encyclopedia', 'portmanteau' ]) - set(wp.processed_wikidump.keys())

	# assert len(wp.en_etys_dl) == 8
	assert wp.en_etys_dl[0]['word'] == 'dictionary', 'Did you change the first items in test.xml?'

	# assert len(wp.en_defs_dl) == 44
	assert wp.en_defs_dl[0]['definition'][:20] == 'A reference work wit'

	# assert len(wp.en_pos_dl) == 16
	assert wp.en_pos_dl[0]['pos_name'] == 'noun'

	# assert len(wp.en_prons_dl) == 9
	assert wp.en_prons_dl[0]['pronunciation'] == '(Received Pronunciation) IPA: /ˈdɪkʃ(ə)n(ə)ɹi/'

	# assert len(wp.etys_dl) == 9
	assert wp.etys_dl[0]['word'] == 'dictionary'

	# assert len(wp.entry_numbers) == 23
	# assert wp.entry_numbers == [1]*23

	assert len(wp.language_dict) > 0
	assert 'xsc-sak-pro' in wp.language_dict

	# assert len(wp.missed_etymologies) == 1
	# assert wp.missed_etymologies[0][0]['wikitext'] == '{{w|Lewis Carroll}}'

	assert wp.next_wl_2_id > 0

	# assert len(wp.node_connections) == 23
	assert wp.node_connections[0][1]['word'] == 'dictionarium'

	# assert len(wp.wikitext_part_array) == 8
	assert wp.wikitext_part_array[0]['{{m|la|-arium||room, place}}']['place'] == 6

	# unmatched words seems to change often
	# assert len(wp.unmatched_words) == 30
	# assert wp.unmatched_words[2][2] == 'Galician'
	# print(wp.unmatched_words)

	assert wp.test == True
	# assert len(wp.table_sources) == 23
	assert wp.store_intermediates == True

def test_wp_etymology_snapshot():
	with open('tests/etymology_snapshot.json', 'r') as f:
		test_cases = json.loads(f.read())

	for en_ety in wp.en_etys_dl:
		test_case = test_cases.get(en_ety['entry_id'])
		if not test_case: continue
		correct_wikitext = test_case['wikitext']
		received_wikitext = en_ety['wikitext']
		assert correct_wikitext == received_wikitext, f'Error on {en_ety["word"]}:{en_ety["language_name"]} Correct wikitext: {correct_wikitext}; received wikitext: {received_wikitext}' 
		correct_etymology = test_case['etymology']
		received_etymology = en_ety['etymology']
		assert correct_etymology == received_etymology, f'Correct etymology: {correct_etymology}; received etymology: {received_etymology}' 

def test_wp_all_connections_snapshot():
	results = {}
	with open('tests/all_connections_snapshot.json', 'r') as f:
		test_cases = json.loads(f.read())

	for c in wp.all_connections: #c[3] is entry_id
		results.setdefault(str(c[3]), set()).add(f'{c[0]}-{c[1]}')

	for en_ety in wp.en_etys_dl:
		e = str(en_ety['entry_id'])
		assert set(test_cases.get(e, [])) == results.get(e, set()), f'Error on {e}'

def test_wp_node_connections_snapshot():
	results = {}
	with open('tests/node_connections_snapshot.json', 'r') as f:
		test_cases = json.loads(f.read())

	for c in wp.node_connections:
		results.setdefault(str(c[2]), set()).add(f'{c[0]["word"]}:{c[0]["language"]}-{c[1]["word"]}{c[1]["language"]}')

	for en_ety in wp.en_etys_dl:
		e = str(en_ety['entry_id'])
		assert set(test_cases.get(e, [])) == results.get(e, set()), f'Error on {e}'

def test_wp_connections():
	all_con_dict = set(f'{w[0]}-{w[1]}' for w in wp.all_connections) # a way to identify if they exist more easily
	assert '{{eeStart|English|dictionary}}-{{bor|en|ML.|dictionarium}}' in all_con_dict 
	assert '{{bor|en|ML.|dictionarium}}-{{der|en|la|dictionarius}}' in all_con_dict 
	assert '{{der|en|la|dictionarius}}-{{m|la|dictio||speaking}}' in all_con_dict  
	assert '{{m|la|dictio||speaking}}-{{m|la|dictus}}' in all_con_dict 
	assert '{{m|la|dictus}}-{{m|la|dīcō||speak}}' in all_con_dict 
	# assert not '{{m|la|dictus}}-{{m|la|-arium||room, place}}' in all_con_dict # Not ready for this one yet