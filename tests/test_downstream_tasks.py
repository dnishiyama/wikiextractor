import sys, os, shutil, json
from wikiextractor.downstream_tasks import *

# for interactive python
# wp = WikiProcessor('/Users/nish/development/git/wikiextractor/tests/wikiextractor_test_dir/', store_intermediates=True, channel='test', dump_file_name='test.xml')

tests_dir = os.path.dirname(__file__)
extraction_dir = tests_dir +'/wikiextractor_test_dir/' # input will be a subdir
os.makedirs(os.path.dirname(extraction_dir), exist_ok=True)
dump_file_name = 'test.xml'

# from dgnutils import close_connectiosn
# close_connections('etymology_explorer_test')

wp = WikiProcessor(extraction_dir, store_intermediates=True, dump_file_name=dump_file_name, channel='test')

def test_multi_parse_wikitext_sentences():
	sentences=['{{wikispecies|test|banana}} This is the test']; cache_file=None; ignore_connection_forming=False
	multi_parse_wikitext_sentences(sentences, cache_file, ignore_connection_forming)

def test_wiki_extract_dump():
	limit = 20
	pages = extract_pages(wp.input_path + wp.dump_file_name, limit=limit); pages
	assert len(pages) == limit
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
	assert '==English==' in get_wikidump_text('loach', dump_file_path)

	pages = extract_pages(dump_file_path, limit=limit)
	assert pages[0]['title'] == 'dictionary', 'Did not ignore ns of non 0 or 118'
	try:
		print(f'Trying to delete existing {output_dir}')
		shutil.rmtree(output_dir)
	except Exception as e:
		print('No output to remove')
	wikiextract_dump(dump_file_path, output_dir, limit = limit)
	with open(output_dir + 'AA/wiki_00', 'r') as f:
		page_data = [json.loads(l) for l in f.readlines()] 
		assert len(page_data) == limit
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
	wp.evaluate_single_word('loach')
	assert wp.node_connections[-1][0]['word'] == 'loach'
	assert wp.all_connections[-1][1]  == '{{l|en|LOH|gloss=loach}}'

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

	wp.process_wikidump(commit=True)
	assert wp.channel == 'test'
	assert wp.database == 'etymology_explorer_test'
	assert len(wp.all_connections) == 27
	assert wp.all_connections[0][0] == '{{eeStart|English|dictionary}}'
	assert len(wp.roots) == 23, 'Did you change the first items in test.xml?'
	assert len(wp.descs) == 23
	assert list(wp.processed_wikidump.keys()) == ['dictionary', 'free', 'thesaurus', 'encyclopedia', 'portmanteau']

	assert len(wp.en_etys_dl) == 8
	assert wp.en_etys_dl[0]['word'] == 'dictionary'

	assert len(wp.en_defs_dl) == 44
	assert wp.en_defs_dl[0]['definition'][:20] == 'A reference work wit'

	assert len(wp.en_pos_dl) == 16
	assert wp.en_pos_dl[0]['pos_name'] == 'noun'

	assert len(wp.en_prons_dl) == 9
	assert wp.en_prons_dl[0]['pronunciation'] == '(Received Pronunciation) IPA/ˈdɪkʃ(ə)n(ə)ɹi/'

	assert len(wp.etys_dl) == 9
	assert wp.etys_dl[0]['word'] == 'dictionary'

	assert len(wp.entry_numbers) == 23
	assert wp.entry_numbers == [1]*23

	assert len(wp.language_dict) > 0
	assert 'xsc-sak-pro' in wp.language_dict

	assert len(wp.missed_etymologies) == 1
	assert wp.missed_etymologies[0][0]['wikitext'] == '{{w|Lewis Carroll}}'

	assert wp.next_wl_2_id > 0

	assert len(wp.node_connections) == 23
	assert wp.node_connections[0][1]['word'] == 'dictionarium'

	assert len(wp.wikitext_part_array) == 8
	assert wp.wikitext_part_array[0]['{{m|la|-arium||room, place}}']['place'] == 6

	# unmatched words seems to change often
	# assert len(wp.unmatched_words) == 30
	# assert wp.unmatched_words[2][2] == 'Galician'
	# print(wp.unmatched_words)

	assert wp.test == True
	assert len(wp.table_sources) == 23
	assert wp.store_intermediates == True