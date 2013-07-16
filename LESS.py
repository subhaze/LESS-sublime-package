import sublime, sublime_plugin, re, os, time

cache_dict = {}

scratch_view = None

def plugin_loaded():
	global scratch_view
	scratch_view = sublime.active_window().create_output_panel('LESS_output')
	scratch_view.set_syntax_file('Packages/LESS/LESS.tmLanguage')

def parse_imports(file_name, view):
	file_path = os.path.split(file_name)[0] + '/'
	pattern = re.compile(r"['\"](.*)['\"]")
	file_list = []
	imports = [view.substr(imports) for imports in view.find_all(r'(@import)(.*);')]
	for _import in imports:
		_file = pattern.search(_import)
		if _file is not None: file_list.append(file_path + _file.group(1))
	return file_list

def parse_file(file_name):
	global scratch_view, cache_dict
	if not file_name.endswith('.less'):
		file_name = file_name + '.less'
	# only parse file if it's being saved or hasn't be before
	# possibly make it optional to always parse import files
	if file_name in cache_dict: return
	try:
		with open(file_name, 'r') as f:
			sublime.active_window().run_command('less_parse_file', {"content": f.read()})
			parse_view(file_name, scratch_view)
	except IOError: pass

def parse_view(file_name, view):
	file_imports = parse_imports(file_name, view)
	for _file in file_imports: parse_file(_file)
	selectors = [
		('var', 'support.constant.variable.css.less'),
		# ('id', 'entity.other.attribute-name.id'),
		# ('class', 'entity.other.attribute-name.class.css'),
		('mixin', 'support.function.css.less')
	]
	results = []
	for selector in selectors:
		temp_results = view.find_by_selector(selector[1])
		temp_results = [(view.substr(var).strip()+'\tLESS '+selector[0], view.substr(var)) for var in temp_results]
		results += list(set(temp_results))
	cache_dict[file_name] = {"dependecies": file_imports, "completions": results}

def get_dependency_files(file_name):
	if file_name not in cache_dict: return []
	depends_on = cache_dict[file_name].get('dependecies')
	if len(depends_on):
		for _file in depends_on:
			depends_on += get_dependency_files(_file)
	return depends_on

class LessParseFileCommand(sublime_plugin.TextCommand):
	global scratch_view
	def run(self, edit, content):
		scratch_view.erase(edit, sublime.Region(0,scratch_view.size()))
		scratch_view.insert(edit, 0, content)

class LessCompletions(sublime_plugin.EventListener):
	global cache_dict
	def on_query_completions(self, view, prefix, locations):
		file_name = view.file_name()
		if file_name and file_name in cache_dict:
			results = []
			file_list = get_dependency_files(file_name)
			for _file in file_list:
				if _file in cache_dict:
					results += cache_dict[_file].get('completions')
			# results = [cache_dict[_file].get('completions') for _file in file_list if _file in cache_dict]
			results = list(set(results))
			results.sort(key=lambda tup: tup[1])
			return (results, 0)
		return ([], 0)
	def on_post_save_async(self, view):
		file_name = view.file_name()
		if file_name is None: return
		parse_view(file_name, view)
