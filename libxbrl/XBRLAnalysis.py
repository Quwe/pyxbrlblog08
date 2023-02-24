from itertools import combinations_with_replacement
from bs4 import BeautifulSoup
from .XMLDataGetter import XMLDataGetter
from .XBRLError import XBRLAnalysisError
import os
import pickle
import copy
import hashlib
from abc import ABCMeta, abstractmethod



class IterableTree(metaclass=ABCMeta):


	@abstractmethod
	def get_root_node(self) :
		pass



	#イテレーターを実装


	#巡回情報スタックへのアクセスは全てこれらの関数郡で行う

	def get_top_walk_info(self):

		if len(self.walk_info_stack) == 0 :
			return None


		else :
			return self.walk_info_stack[-1]

	def pop_walk_info(self) :
		if len(self.walk_info_stack) == 0 :
			return None

		else :
			return self.walk_info_stack.pop()


	def append_walk_info(self, walk_info) :
		self.walk_info_stack.append(walk_info)



	#巡回状況を初期化する
	#デフォルトはルート
	def init_walking_status(self) :
		self.walk_info_stack = list()
		self.walk_info_stack.append(WalkInfo(self.get_root_node()))


	#与えられたノードをルートとして巡回する
	def set_walking_root(self, node) :
		self.walk_info_stack = list()
		self.walk_info_stack.append(WalkInfo(node))



	#イテレータのインターフェース関数
	def __iter__(self):

		return self

	#イテレータのインターフェース関数
	def __next__(self):

		return self.walk_next_node()


	#次の要素に巡回する
	#
	#巡回情報スタックに応じて動作する
	#
	#スタックの最上位の要素を巡回していく
	#子要素がある時はスタックし、親要素に戻るときはポップする
	#スタックが空になった時が巡回を終了するべき時である
	#
	#スタックの一番底が巡回対象となる木構造のルートとなっている
	#部分木のみ巡回したければ、このスタックの一番底を部分木のルートにしておけばよい
	#
	#
	#巡回先の決定アルゴリズム
	#
	#1.巡回情報スタックが空なら巡回を終える
	#  巡回を終える際はスタックに次に巡回する木構造の
	#  最上位ノード情報のみがある状態にしておく
	#
	#2.スタックの最上位が未巡回ならそこを巡回する
	#
	#3.スタックの最上位の子要素を巡回する
	#  子要素を巡回する際はスタックに子要素ノードの情報を積み
	#　再度1から処理を継続する
	#
	#4.子要素を巡回しきったら、親要素を巡回する
	#  親要素を巡回する際はスタックをポップし
	#　再度1から処理を継続する
	#
	def walk_next_node(self):

		#巡回情報が空なら巡回は完了している	
		top_walk_info = self.get_top_walk_info()
		if top_walk_info == None :
			self.end_walking()


		#自身を巡回してないなら自身を巡回する
		if top_walk_info.current_node_returned == False :
			top_walk_info.current_node_returned = True
			return top_walk_info.current_node	


		#いまのノードにとって子ノードの巡回がはじめてなら
		#子ノードの巡回情報の初期化が必要
		if top_walk_info.last_returned_child_index == -1 and len(top_walk_info.current_node.get_children()) != 0 :
			top_walk_info.number_of_children =  len(top_walk_info.current_node.get_children())

			#初回だけ子ノードのソートを実施する
			top_walk_info.current_node.get_children().sort()


		#いま巡回する子ノードのインデックスは前回巡回した子ノードのインデックスの次である
		child_index = top_walk_info.last_returned_child_index + 1


		#最後の子ノードを巡回済みであれば親の巡回を再開する
		if top_walk_info.number_of_children <=  child_index :
			self.pop_walk_info()
			return self.walk_next_node()	


		#子ノードを巡回する
		top_walk_info.last_returned_child_index = top_walk_info.last_returned_child_index + 1
		self.append_walk_info(WalkInfo(top_walk_info.current_node.get_children()[child_index]))	
		return self.walk_next_node()


		#ここに到達することはあり得ない


	#巡回を終了する
	def end_walking(self) :
		self.init_walking_status()
		raise StopIteration()



#巡回情報
class WalkInfo():

	def __init__(self, current_node):
		self.current_node = current_node

		#自身を巡回済みか否か
		self.current_node_returned = False

		#子ノードの巡回状況を保持
		self.last_returned_child_index = -1 
		self.number_of_children = 0




#リンクベースファイルのツリー構造を保存する
class XBRLLinkBaseTree(IterableTree) :

	def __init__(self, xbrl_path_data) :

		self.__root_node = None
		self.__rol_list = list()
		self.__xbrl_path_data = xbrl_path_data


	def get_root_node(self) :
		return self.__root_node

	def set_root_node(self, root_node) :
		self.__root_node = root_node

	def get_rol_list(self) :
		return self.__rol_list


	#ノードを検索する
	def search_node(self, id) :

		result = None

		for elm in self :

			if elm.get_id() == id :
				result = elm

		return result



	def get_xbrl_path_data(self) :
		return self.__xbrl_path_data


	def show_tree(self, show_node_id = 'root') :

		#rootおよびrol_list中のノードのみ受け付ける
		if show_node_id != 'root' and show_node_id not in self.get_rol_list() :

			print('不正なノード指定:' + show_node_id)
			return


		#表示ルートノードの設定
		show_node = self.search_node(show_node_id)

		#木構造の表示処理
		self.__print_all_node(show_node, 0)



	#指定されたノードに連なるノードを全て表示する
	def __print_all_node(self, root_node, depth):


		print('     '*depth + str(root_node))

		root_node.get_children().sort()
		for child in root_node.get_children() :
			self.__print_all_node(child, depth + 1)

	@staticmethod
	def search_node_that_have_target_id_child(node, id) :

		result_node = None
		result_index = -1

		#まず自分自身を調べる
		for index, child in enumerate(node.get_children()) :

			if child.get_id() == id :

				result_node = node
				result_index = index
				break


		#発見したら結果を返す
		if result_node != None :
			return result_node, result_index


		#次に子供を調べる
		for child in node.get_children() :

			result_tuple = XBRLLinkBaseTree.search_node_that_have_target_id_child(child, id)
			if result_tuple[0] != None :

				return result_tuple[0], result_tuple[1]


		#発見できず
		return None, -1


	#xsdファイルの読み込み
	def read_xsd_file(self, rol_id) :

		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.get_rol_list() :
			return


		#木構造巡回のルートを設定する
		self.set_walking_root(self.search_node(rol_id))


		#xsdファイルを検索し、各ノードの詳細情報から用途を調べる
		for node in self :

			#role要素は処理しない
			if node.get_node_kind() == 'document_name' :
				continue

			soup = XMLDataGetter.get(node.get_xsd_uri() )
			if soup == None :

				raise XBRLAnalysisError('スキーマファイルが存在しない:' + node.get_xsd_uri())


			detail_elm = soup.select_one('#' + node.get_id() )
			if detail_elm == None :

				raise XBRLAnalysisError('スキーマファイルに該当要素無し:' + node.get_href())


			#必要な属性を取得
			tmp_name = detail_elm.get('name').split(':')[-1]
			tmp_period_type = detail_elm.get('xbrli:periodType').split(':')[-1]
			tmp_type = detail_elm.get('type').split(':')[-1]
			tmp_substitutionGroup = detail_elm.get('substitutionGroup').split(':')[-1]


			#abstractが設定されていない場合はfalseと判断
			#暫定
			if detail_elm.get('abstract') == None :
				tmp_abstract = 'false'
			else :
				tmp_abstract = detail_elm.get('abstract').split(':')[-1]


			#属性の値から用途を判別
			if 'Heading' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'identifierItem' and tmp_abstract == 'true' :
				node.set_usage('heading')

			elif 'Abstract' in tmp_name  and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('title')

			elif 'Table' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'hypercubeItem' and tmp_abstract == 'true' :
				node.set_usage('table')

			elif 'Axis' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'dimensionItem' and tmp_abstract == 'true' :
				node.set_usage('axis')

			elif 'Member' in tmp_name and tmp_type == 'domainItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('member')

			elif 'LineItems' in tmp_name and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('line_items')

			elif tmp_abstract == 'false' and ( tmp_type == 'monetaryItemType' or \
								tmp_type == 'perShareItemType' or \
								tmp_type == 'sharesItemType' or \
								tmp_type == 'percentItemType' or \
								tmp_type == 'decimalItemType' or \
								tmp_type == 'nonNegativeIntegerItemType') :
				node.set_usage('number')

			elif tmp_abstract == 'false' and ( tmp_type == 'dateItemType') :
				node.set_usage('date')

			elif 'TextBlock' in tmp_name and tmp_abstract == 'false' and ( tmp_type == 'textBlockItemType' ) :

				node.set_usage('text_block')

			elif tmp_abstract == 'false' and tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' :

				node.set_usage('text')

			elif tmp_type == 'stringItemType' and tmp_substitutionGroup == 'item' and tmp_abstract == 'true' :
				node.set_usage('title')

			else :
				raise XBRLAnalysisError('要素用途の判定結果例外:'+detail_elm.prettify())


			node.set_name(tmp_name)
			node.set_period_type(tmp_period_type)



	#名称リンクベースファイル(日本語)を読み込み、各ノードの日本語名称を取得する
	def read_jp_lab_file(self, rol_id) :

		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.get_rol_list() :
			return


		#木構造巡回のルートを設定する
		self.set_walking_root(self.search_node(rol_id))



		#名称リンクベースファイル（日本語)を読み込む
		labfile_structure_dicts = NameLinkBaseAnalysis.get_JPNameStructureDict(self.get_xbrl_path_data())



		#各ノードの日本語名称を設定する
		labfile_list = NameLinkBaseAnalysis.get_JPNameLinkBaseList(self.get_xbrl_path_data())
		for node in self :

			#role要素は処理しない
			if node.get_node_kind() == 'document_name' :
				continue



			#要素のスキーマファイルのURIから参照するべき名称リンクベースを取得する
			targeted_labfile = None

			schema_url = node.get_xsd_uri()

			if schema_url.startswith('http') :
				sep = '/'
			else :
				sep = os.sep

			schema_dir = sep.join(schema_url.split(sep)[0:-1])

			for labfile in labfile_list :

				if labfile.startswith(schema_dir) :
					targeted_labfile = labfile
					break

			if targeted_labfile == None :
				raise XBRLAnalysisError('ノードに対応する名称リンクベースファイルを発見できませんでした')


			#名称リンクベースファイルに対応するレコードリストを取得する
			label_records = labfile_structure_dicts[targeted_labfile]


			#レコードリストを検索する
			jp_str = None

			for record in label_records :

				if node.get_id() == record.id and record.role == node.get_using_role() :

					jp_str = record.jp_str
					break


			#デフォルトは標準ラベルを用いる
			if jp_str == None :
				for record in label_records :
					if node.get_id() == record.id and record.role == 'http://www.xbrl.org/2003/role/label' :

						jp_str = record.jp_str
						break


			node.set_jp_label(jp_str)




#定義リンクベースファイルのツリー構造
class XBRLDefinitionLinkBaseTree(XBRLLinkBaseTree):

	def __init__(self, xbrl_path_data):

		super().__init__(xbrl_path_data)



		#データの読み込みに成功しようがどうだろうがルートだけは用意しておく
		self.set_root_node(XBRLViewLinkBaseNode('document_root', 'root'))
		self.get_root_node().set_href('root')


		#木構造巡回のための復帰情報を詰んでおくためのスタック
		#通常はルートから巡回を開始する
		self.init_walking_status() 


		#定義リンクベースファイルの解析を始める
		soup = XMLDataGetter.get(self.get_xbrl_path_data().get_def_file_path())


		#親子関係読み込み後のhref取得に用いる
		roleRef_elems = soup.select('roleRef')
		loc_elems = soup.select('loc')	


		#roleRef要素の一覧を保存
		for elem in roleRef_elems :
			self.get_rol_list().append( elem.get('xlink:href').split('#')[-1] )



		#まずはリンク構造(親子関係)を読み込み木構造を生成する


		#definitionLinkごとに構造を取得する
		document_number = 0
		for primary_item in soup.select('definitionLink'):

			document_number = document_number + 1

			#大項目の名称を取得
			primary_item_name = primary_item.get('xlink:role')
			sub_root_node = XBRLDefinitionLinkBaseNode(primary_item_name, 'document_name')

			#大項目のhref属性を設定
			for elem in roleRef_elems :
				if elem.get('roleURI') == sub_root_node.get_label_in_linkbase() :
					sub_root_node.set_href(elem.get('xlink:href') )
					break


			self.get_root_node().append_child(sub_root_node, document_number)


			#各要素を保存するための辞書
			tree_dict = {}


			#definitionLink内の各要素の親子関係を取得し保存する
			for elem in primary_item.select('definitionArc'):

				parent_name = elem.get('xlink:from')
				child_name = elem.get('xlink:to')
				order_str = elem.get('order')

				arcrole_str = elem.get('xlink:arcrole')


				order = None
				if order_str != None :
					order = float(order_str)

				parent = None
				child = None


				if parent_name not in tree_dict:
					parent = XBRLDefinitionLinkBaseNode(parent_name, 'content')
					tree_dict[parent_name] = parent
				else :
					parent = tree_dict[parent_name]


				if child_name not in tree_dict:
					child = XBRLDefinitionLinkBaseNode(child_name, 'content')
					tree_dict[child_name] = child
				else :
					child = tree_dict[child_name]


				parent.append_child(child, order)
				child.set_parent(parent)


				if arcrole_str == 'http://xbrl.org/int/dim/arcrole/dimension-default' :
					child.set_dimension_default_flag(True)


			#親子関係を読み込めたら、各項目のhref属性を設定する
			for key in tree_dict.keys():

				node = tree_dict[key]

				for elem in loc_elems :
					if elem.get('xlink:label') == node.get_label_in_linkbase() :

						#loc要素の中にはhref要素のURIがローカルファイルのケースが存在する
						#(提出者の独自要素の場合)
						#この場合はhrefの値を参照可能なパスに修正する
						tmp_href = elem.get('xlink:href')
						if not tmp_href.startswith('http') :
							tmp_href = os.path.join(self.get_xbrl_path_data().get_xbrl_dir_path(), tmp_href)


						node.set_href(tmp_href)
						break




			#保存結果には親が設定されていないノードが存在するため、ここで設定する
			no_parent_node_list = list()
			for key in tree_dict.keys():
				current_node = tree_dict[key]

				if current_node.get_parent() == None :
					no_parent_node_list.append(current_node)


			#idが*Heading*となるノードが最上位ノードなのでこれをまず探す
			#ただし、これは命名規則によるものなので副作用があるかもしれない
			#親無しノードのidとしてHeadingが使われていないという前提の処理
			#もしこれがダメならスキマーファイルを調べて、更に絞り込む必要がある
			heading_node = None
			for no_parent_node in no_parent_node_list :
				if 'Heading' in no_parent_node.get_id() :
					heading_node = no_parent_node
					break


			#Headingノードが存在しないなら
			#親無しノードが一つしか存在しない場合のみ処理可能
			if heading_node == None :

				if len(no_parent_node_list) == 1 :

					heading_node = no_parent_node_list[0]

				else :

					raise Exception('no heading node error')


			sub_root_node.append_child(heading_node, 1.0)
			no_parent_node_list.remove(heading_node)


			#Headingノード以外の親無しを処理する
			while len(no_parent_node_list) > 0 :

				#Headingから辿って、子に親無しを持つノードを探す

				#(node, child_index)
				result_tuple = (None, -1)
				source_node = None
				for no_parent_node in no_parent_node_list :

					result_tuple = XBRLLinkBaseTree.search_node_that_have_target_id_child(heading_node, no_parent_node.get_id())
					if result_tuple[0] != None :
						source_node = no_parent_node
						break

				#親無しはHeading以下に必ず存在する
				if result_tuple[0] == None :
					raise Exception('no parent node is not exists in heading node')


				node_that_have_target_label_child = result_tuple[0]
				child_index = result_tuple[1]


				#デフォルトディメンションフラグと順序は親無しには絶対設定されていない
				#したがって、挿入先のものを使用する
				source_node.set_order(node_that_have_target_label_child.get_children()[child_index].get_order())
				source_node.set_dimension_default_flag(node_that_have_target_label_child.get_children()[child_index].get_dimension_default_flag())

				#親無しを挿入する
				node_that_have_target_label_child.get_children()[child_index] = source_node

				no_parent_node_list.remove(source_node)




#XBRLの構造を保存するツリー構造
class XBRLStructureTree(XBRLLinkBaseTree):


	#XBRLの構造は表示リンクベースファイルを元に生成する
	def __init__(self, xbrl_path_data):

		super().__init__(xbrl_path_data)


		self.__context_list = list()


		#データの読み込みに成功しようがどうだろうがルートだけは用意しておく
		self.set_root_node(XBRLStructureNode('document_root', 'root'))
		self.get_root_node().set_href('root')


		#木構造巡回のための復帰情報を詰んでおくためのスタック
		#通常はルートから巡回を開始する
		self.init_walking_status() 


		#表示リンクベースファイルの解析を始める
		soup = XMLDataGetter.get(self.get_xbrl_path_data().get_pre_file_path())


		#親子関係読み込み後のhref取得に用いる
		roleRef_elems = soup.select('roleRef')
		loc_elems = soup.select('loc')	


		#roleRef要素の一覧を保存
		for elem in roleRef_elems :
			self.get_rol_list().append( elem.get('xlink:href').split('#')[-1] )



		#まずはリンク構造(親子関係)を読み込み木構造を生成する


		#presentationLinkごとに構造を取得する
		document_number = 0
		for primary_item in soup.select('presentationLink'):

			document_number = document_number + 1

			#大項目の名称を取得
			primary_item_name = primary_item.get('xlink:role')
			sub_root_node = XBRLStructureNode(primary_item_name, 'document_name')

			#大項目のhref属性を設定
			for elem in roleRef_elems :
				if elem.get('roleURI') == sub_root_node.get_label_in_linkbase() :
					sub_root_node.set_href(elem.get('xlink:href') )
					break


			self.get_root_node().append_child(sub_root_node, document_number)


			#各要素を保存するための辞書
			tree_dict = {}


			#presentationLink内の各要素の親子関係を取得し保存する
			for elem in primary_item.select('presentationArc'):

				parent_name = elem.get('xlink:from')
				child_name = elem.get('xlink:to')
				order_str = elem.get('order')
				preferred_label = elem.get('preferredLabel')

				order = None
				if order_str != None :
					order = float(order_str)

				parent = None
				child = None


				if parent_name not in tree_dict:
					parent = XBRLStructureNode(parent_name, 'content')
					tree_dict[parent_name] = parent
				else :
					parent = tree_dict[parent_name]


				if child_name not in tree_dict:
					child = XBRLStructureNode(child_name, 'content')
					tree_dict[child_name] = child
				else :
					child = tree_dict[child_name]


				parent.append_child(child, order)
				child.set_parent(parent)


				if preferred_label != None :
					child.set_preferred_label(preferred_label)



			#親子関係を読み込めたら、各項目のhref属性を設定する
			for key in tree_dict.keys():

				node = tree_dict[key]

				for elem in loc_elems :
					if elem.get('xlink:label') == node.get_label_in_linkbase() :

						#loc要素の中にはhref要素のURIがローカルファイルのケースが存在する
						#(提出者の独自要素の場合)
						#この場合はhrefの値を参照可能なパスに修正する
						tmp_href = elem.get('xlink:href')
						if not tmp_href.startswith('http') :
							tmp_href = os.path.join(self.get_xbrl_path_data().get_xbrl_dir_path(), tmp_href)


						node.set_href(tmp_href)
						break




			#保存結果には親が設定されていないノードが存在するため、ここで設定する
			no_parent_node_list = list()
			for key in tree_dict.keys():
				current_node = tree_dict[key]

				if current_node.get_parent() == None :
					no_parent_node_list.append(current_node)


			#idが*Heading*となるノードが最上位ノードなのでこれをまず探す
			#ただし、これは命名規則によるものなので副作用があるかもしれない
			#親無しノードのidとしてHeadingが使われていないという前提の処理
			#もしこれがダメならスキマーファイルを調べて、更に絞り込む必要がある
			heading_node = None
			for no_parent_node in no_parent_node_list :
				if 'Heading' in no_parent_node.get_id() :
					heading_node = no_parent_node
					break


			#EDINET XBRLのガイドラインを見る限り
			#Headingノードは必ず存在するはず
			if heading_node == None :
				raise Exception('no heading node error')


			sub_root_node.append_child(heading_node, 1.0)
			no_parent_node_list.remove(heading_node)


			#Headingノード以外の親無しを処理する
			while len(no_parent_node_list) > 0 :

				#Headingから辿って、子に親無しを持つノードを探す

				#(node, child_index)
				result_tuple = (None, -1)
				source_node = None
				for no_parent_node in no_parent_node_list :

					result_tuple = XBRLLinkBaseTree.search_node_that_have_target_id_child(heading_node, no_parent_node.get_id())
					if result_tuple[0] != None :
						source_node = no_parent_node
						break

				#親無しはHeading以下に必ず存在する
				if result_tuple[0] == None :
					raise Exception('no parent node is not exists in heading node')


				node_that_have_target_label_child = result_tuple[0]
				child_index = result_tuple[1]


				#優先ラベルと順序は親無しには絶対設定されていない
				#したがって、挿入先のものを使用する
				source_node.set_order(node_that_have_target_label_child.get_children()[child_index].get_order())
				source_node.set_preferred_label(node_that_have_target_label_child.get_children()[child_index].get_preferred_label())

				#親無しを挿入する
				node_that_have_target_label_child.get_children()[child_index] = source_node

				no_parent_node_list.remove(source_node)


		#優先ラベルを設定する
		self.__set_preferred_label(self.get_root_node(), None)




	#ディメンジョンデフォルト情報を設定する
	def set_dimension_default(self, def_linkbase_tree, rol_id) :


		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.get_rol_list() :
			return



		#定義リンクベースファイルに該当する大項目がなければ
		#ディメンションデフォルトとなるメンバーも当然存在しない
		if rol_id not in def_linkbase_tree.get_rol_list() :

			return


		#メンバー要素毎に処理する
		view_linkbase_rol_node = self.search_node(rol_id)
		self.set_walking_root(view_linkbase_rol_node)
		for target_node in self :

			#メンバー以外は処理しない
			if target_node.get_usage() != 'member' :
				continue


			#定義リンクベースファイルの大項目から
			#同じidとなるノードを探す
			def_linkbase_node_list = list()

			def_linkbase_rol_node = def_linkbase_tree.search_node(rol_id)
			def_linkbase_tree.set_walking_root(def_linkbase_rol_node)
			for def_linkbase_node in def_linkbase_tree :

				if def_linkbase_node.get_id() == target_node.get_id() :

					def_linkbase_node_list.append(def_linkbase_node)



			#見つかったノードにディメンションデフォルトとなるノードが存在するか
			dimension_default_node_is_exist = False
			for def_linkbase_node in def_linkbase_node_list :

				if def_linkbase_node.get_dimension_default_flag() == True :

					dimension_default_node_is_exist = True
					break


			#存在するならメンバー要素をディメンションデフォルトに設定する
			if dimension_default_node_is_exist == True :

				target_node.set_dimension_default_flag(True)


	#優先ラベル情報を設定する
	def __set_preferred_label(self, target_node, parent_preferred_label):

		#親の優先ラベルが設定されており、設定対象の優先ラベルが設定されていない場合のみ
		#設定対象のノードの優先ラベルを設定する

		if target_node.get_preferred_label() == None and parent_preferred_label != None :

			target_node.set_preferred_label(parent_preferred_label)


		for child in target_node.get_children() :
			self.__set_preferred_label(child, target_node.get_preferred_label())




	#特定の大項目内のtable構造を取得する
	#軸名称をkeyとしてメンバー要素のリストを格納する辞書データ
	def get_table_structure_dict(self, rol_id):


		table_structure_dict = {}

		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.get_rol_list() :
			return None


		#軸要素を探す
		axis_node_list = list()
		self.set_walking_root(self.search_node(rol_id))
		for node in self :

			if node.get_usage() == 'axis' :

				axis_node_list.append(node)


		#各軸を調べtable構造を生成する
		for axis_node in axis_node_list :

			member_node_list = list()

			self.set_walking_root(axis_node)
			for node in self :

				if node.get_usage() == 'member' :

					member_node_list.append(node)

			table_structure_dict[axis_node.get_id()] = member_node_list

		return table_structure_dict


	#インスタンス文書を読み込み、データを取得する
	def read_instance_data(self, rol_id, xbrl_instance_file_analyzer) :

		#存在しないrolを指定された場合は処理しない
		if rol_id not in self.get_rol_list() :
			return


		#指定された大項目の構造を取得
		table_structure_dict = self.get_table_structure_dict(rol_id)

		#軸が存在しないか、軸1つまたは2つある場合のみを受け入れる
		if len(table_structure_dict.keys()) < 3:

			pass

		else :

			raise XBRLAnalysisError('テーブルの構造が不正(テーブルが存在するが軸の数が3以上):' + rol_id)



		#インスタンス文書からコンテキストを取得
		context_list = xbrl_instance_file_analyzer.get_context_list()


		#軸を使って1回目のコンテキストの選別を行う

		axis_id_list = list()
		axis_id_list.extend(table_structure_dict.keys())

		XBRLInstanceFileAnalysis.select_context_by_axis(context_list, axis_id_list)


		#連結or単体軸が存在するならその軸のメンバを使って2回目の選別を行う
		if 'jppfs_cor_ConsolidatedOrNonConsolidatedAxis' in axis_id_list :

			#軸のメンバーを取得
			member_list = table_structure_dict['jppfs_cor_ConsolidatedOrNonConsolidatedAxis']
			if len(member_list) != 1 :
				raise XBRLAnalysisError('連結or単体軸のメンバー構成が不正:' + rol_id)

			member_id = member_list[0].get_id()
			dimension_default_flag = member_list[0].get_dimension_default_flag()

			XBRLInstanceFileAnalysis.select_context_by_member(context_list, 'jppfs_cor_ConsolidatedOrNonConsolidatedAxis', member_id, dimension_default_flag)



		#列方向の軸を取得する
		col_axis_id = None
		col_axis_member_list = None
		for axis_id in table_structure_dict.keys() :

			#連結or単体軸は読み飛ばす
			if axis_id == 'jppfs_cor_ConsolidatedOrNonConsolidatedAxis' :

				continue

			col_axis_id = axis_id
			col_axis_member_list = table_structure_dict[axis_id]

			break



		#各要素ごとにコンテキストの選別を行い、コンテキスト毎のデータを取得する
		self.set_walking_root(self.search_node(rol_id))
		for node in self :


			#要素が数値、日時、テキストブロック、テキストである場合のみ処理を行う
			node_usage = node.get_usage()
			if not (node_usage == 'number' or node_usage == 'date' or node_usage == 'text_block' or node_usage == 'text') :
				continue

			#print('要素:' + node.get_jp_label() + ',' + node.get_id())

			#要素の期間タイプに応じてコンテキストを選別する
			node_context_list = copy.deepcopy(context_list)
			XBRLInstanceFileAnalysis.select_context_by_period_type(node_context_list, node.get_period_type())

			#列方向の軸の各メンバー毎にコンテキストを選別し、データを取得
			if col_axis_member_list != None and col_axis_id != None:
				
				member_to_contextdict_dict = {}

				for col_axis_member in col_axis_member_list :

					#print('メンバー:' + col_axis_member.get_jp_label() + ',' + col_axis_member.get_id())
					member_context_list = copy.deepcopy(node_context_list)
					XBRLInstanceFileAnalysis.select_context_by_member(member_context_list, col_axis_id, col_axis_member.get_id(), col_axis_member.get_dimension_default_flag())
					
					context_to_data_dict = {}
					
					for context in member_context_list :
						data = xbrl_instance_file_analyzer.get_data_from_instance_file(node.get_id(),context.get_name())
						context_to_data_dict[context.get_name()] = data
						#print('[' + context.get_name() + ']'+ '[' + data + ']')

					member_to_contextdict_dict[col_axis_member.get_id()] = context_to_data_dict

				node.set_xbrl_data(XBRLData(member_to_contextdict_dict))

			#列方向の軸が存在しないならコンテキストの選別せずにデータを取得
			else :
				member_to_contextdict_dict = {}
				context_to_data_dict = {}

				for context in node_context_list :
					data = xbrl_instance_file_analyzer.get_data_from_instance_file(node.get_id(),context.get_name())
					context_to_data_dict[context.get_name()] = data
					#print('[' + context.get_name() + ']'+ '[' + data + ']')

				member_to_contextdict_dict['no member'] = context_to_data_dict
				node.set_xbrl_data(XBRLData(member_to_contextdict_dict))


#IterableTreeを構成するノード
class IterableNode(metaclass=ABCMeta):


	@abstractmethod
	def get_children(self) :
		pass


	@abstractmethod
	def get_order(self) :
		pass

	@abstractmethod
	def set_order(self) :
		pass

	def __lt__(self, other):
		return self.get_order() < other.get_order()



#リンクベースファイルを構成するノード
class LinkBaseNode(IterableNode) :


	def __init__(self, label_in_linkbase, node_kind):

		#ノードの種別
		# 'root'          読み込みのために存在
		# 'document_name' 有報表示構造における大項目
		# 'content'       大項目の下にある構造要素
		self.__node_kind = node_kind


		#表示リンクベースファイル中のラベル属性
		self.__label_in_linkbase = label_in_linkbase

		#親要素からみた子要素の順序
		self.__order = None

		#親要素
		self.__parent = None

		#子要素
		self.__children = list()

		#スキーマファイル中要素のURI
		self.__href = None

		#スキーマファイル中のID
		self.__id = None


		#ノードの用途
		#ノードの名称
		#区間種別
		#スキーマファイルを調査し設定
		self.__usage = None
		self.__name = None
		self.__period_type = None


		#ノードの日本語ラベル
		#名称リンクベースファイルを調査し設定
		self.__jp_label = None


	#href要素を設定する
	def set_href(self, href) :

		self.__href = href
		self.__id = href.split('#')[-1]


	#子ノードを追加する(順序付き)
	def append_child(self, child, order):
		child.__order = order
		self.__children.append(child)


	#スキーマファイルのURIを取得する
	def get_xsd_uri(self) :
		return self.__href.split('#')[0]

	def get_id(self) :
		return self.__id

	def set_usage(self, usage) :
		self.__usage = usage

	def get_usage(self) :
		return self.__usage

	def get_href(self) :
		return self.__href

	def set_name(self, name) :
		self.__name = name

	def get_name(self) :
		return self.__name

	def set_period_type(self, period_type):
		self.__period_type = period_type

	def get_period_type(self):
		return self.__period_type


	def get_order(self) :
		return self.__order

	def set_order(self, order) :
		self.__order = order


	def get_children(self) :
		return self.__children

	def get_label_in_linkbase(self) :
		return self.__label_in_linkbase


	def get_node_kind(self) :
		return self.__node_kind

	def get_parent(self) :
		return self.__parent

	def set_parent(self, parent) :
		self.__parent = parent

	def set_jp_label(self, jp_label) :
		self.__jp_label = jp_label

	def get_jp_label(self) :
		return self.__jp_label

	def __lt__(self, other):
		return self.__order < other.__order

	def __str__(self) :

		return '(' + str(self.get_usage()) + ')' + str(self.get_id()) + '(' + str(self.get_jp_label()) + ')'


#定義リンクベースファイルのノード
class XBRLDefinitionLinkBaseNode(LinkBaseNode):


	def __init__(self, label_in_def_linkbase, node_kind):


		super().__init__(label_in_def_linkbase, node_kind)


		#ディメンションデフォルトフラグ
		self.__dimension_default_flag = False


	def set_dimension_default_flag(self, dimension_default_flag):

		self.__dimension_default_flag = dimension_default_flag

	def get_dimension_default_flag(self):

		return self.__dimension_default_flag

	def get_using_role(self):
		return 'http://www.xbrl.org/2003/role/verboseLabel'

	def __str__(self) :

		description_str = super().__str__()

		if self.get_dimension_default_flag() == True :

			description_str = description_str + '[' +'dimension-default' + ']'

		return description_str


#表示リンクベースファイルのノード
class XBRLViewLinkBaseNode(LinkBaseNode):


	def __init__(self, label_in_pre_linkbase, node_kind):


		super().__init__(label_in_pre_linkbase, node_kind)


		#優先ラベル
		self.__preferred_label = None


	def get_using_role(self):
		return self.__preferred_label

	def get_preferred_label(self):
		return self.__preferred_label

	def set_preferred_label(self, preferred_label) :
		self.__preferred_label = preferred_label


	def __str__(self) :

		description_str = super().__str__()

		if self.get_preferred_label() != None :

			description_str = description_str + '[' + self.get_preferred_label() +']'

		return description_str



#XBRLの構造を保存するノード
class XBRLStructureNode(XBRLViewLinkBaseNode):

	def __init__(self, label_in_pre_linkbase, node_kind):

		super().__init__(label_in_pre_linkbase, node_kind)


		#ディメンションデフォルトフラグ
		self.__dimension_default_flag = False

		#XBRLのインスタンス文書から取得できるデータ
		self.__xbrl_data = None


	def set_dimension_default_flag(self, dimension_default_flag):

		self.__dimension_default_flag = dimension_default_flag

	def get_dimension_default_flag(self):

		return self.__dimension_default_flag

	def set_xbrl_data(self, xbrl_data) :

		self.__xbrl_data = xbrl_data

	def get_xbrl_data(self) :

		return self.__xbrl_data


	def __str__(self) :

		description_str = super().__str__()

		if self.get_dimension_default_flag() == True :

			description_str = description_str + '[' +'dimension-default' + ']'


		return description_str

class NameLinkBaseAnalysis():

	@staticmethod
	def get_JPNameLinkBaseList(xbrl_path_data):


		#本XBRLが参照する名称リンクベースファイル(日本語)の一覧を取得する
		soup = XMLDataGetter.get(xbrl_path_data.get_xsd_file_path())

		labfile_list = list()

		for elm in  soup.select('linkbaseRef') :

			tmp_href = elm.get('xlink:href')
			if tmp_href.startswith('http') and tmp_href.endswith('_lab.xml') :
				labfile_list.append(tmp_href)

		if os.path.exists(xbrl_path_data.get_lab_file_path()) :
			labfile_list.append(xbrl_path_data.get_lab_file_path())


		return labfile_list


	@staticmethod
	def get_JPNameStructureDict(xbrl_path_data):


		labfile_list = NameLinkBaseAnalysis.get_JPNameLinkBaseList(xbrl_path_data)


		#名称リンクベースファイル（日本語)を読み込む
		labfile_structure_dicts = {}

		for labfile in labfile_list :

			jp_str_label_records = list()

			#まずローカルに名称リンクベースを読み込んだデータがないか確認する
			#存在するなら過去の読み込み結果を使う

			hash_str = hashlib.sha256(labfile.encode('utf-8')).hexdigest()
			bin_file_name = '.' + os.sep + 'labfile' + os.sep + 'labfile_structure_' + labfile.translate(str.maketrans('/\\.:', '____')) +'_' + hash_str

			if os.path.isfile(bin_file_name) :

				with open(bin_file_name, 'rb') as f:

					jp_str_label_records = pickle.load(f)
					labfile_structure_dicts[labfile] = jp_str_label_records

				continue


			#ファイルが存在しないなら一から読み込み処理を実行する
			jp_str_label_records = list()

			soup = XMLDataGetter.get(labfile)

			loc_elms= soup.select('loc')
			label_arc_elms = soup.select('labelArc')
			label_elms =  soup.select('label')


			for loc_elm in loc_elms :


				#loc要素から要素IDに対応するラベルを辿るためのリンク名称を取得する
				elm_href =  loc_elm.get('xlink:href')
				elm_id = elm_href.split('#')[-1]

				link_name = loc_elm.get('xlink:label')


				#リンク名からIDにリンクされているラベルを取得する
				for label_arc_elm in label_arc_elms :

					if not label_arc_elm.get('xlink:from') == link_name :

						continue


					label_id = label_arc_elm.get('xlink:to')

					for label_elm in label_elms :


						if not label_elm.get('xlink:label') == label_id :

							continue

						jp_label = str(label_elm.string)
						label_role = label_elm.get('xlink:role')


						jp_str_label_records.append(JPStrLabelRecord(elm_id, label_role, jp_label))




			labfile_structure_dicts[labfile] = jp_str_label_records


			with open(bin_file_name, 'wb') as f:

				pickle.dump(jp_str_label_records, f)



		return labfile_structure_dicts



#名称リンクベースファイルのレコード
class JPStrLabelRecord():


	def __init__(self, id, role, jp_str):

		self.id = id
		self.role = role
		self.jp_str = jp_str



class XBRLInstanceFileAnalysis() :
	
	def __init__(self, xbrl_path_data):

		self.__xbrl_instance_file_soup = XMLDataGetter.get(xbrl_path_data.get_xbrl_file_path())
		self.__read_context()


	#コンテキスト定義の読み込み
	def __read_context(self) :

		self.__context_list = list()


		#xbrlファイルを調査する
		context_elms = self.__xbrl_instance_file_soup.select('context')
		for context_elm in context_elms :

			context_name = context_elm.get('id')

			period_elm = context_elm.select_one('period')

			if period_elm == None :

				raise XBRLAnalysisError('period elm is nothing')


			period_type = None

			if 'Instant' in context_name :

				period_type = 'instant'

			elif 'Duration' in context_name :

				period_type = 'duration'

			if period_type == None :
				raise XBRLAnalysisError('period type error')


			instant_date = None
			start_date = None
			end_date = None
			if period_type == 'instant' :

				instant_date = period_elm.select_one('instant').get_text()

			else :

				start_date = period_elm.select_one('startDate').get_text()
				end_date = period_elm.select_one('endDate').get_text()



			scenario_elm = context_elm.select_one('scenario')
			axis_to_member_tuple_list = list()
			if scenario_elm != None :

				axis_elms = scenario_elm.select('explicitMember')
				for axis_elm in axis_elms :
					axis_to_member_tuple_list.append( (axis_elm.get('dimension').replace(':', '_') \
												, axis_elm.get_text().replace(':', '_')) )


			context_data = Context(context_name, \
						period_type, \
						instant_date, \
						start_date, \
						end_date, \
						axis_to_member_tuple_list)

			self.__context_list.append(context_data)


	def get_data_from_instance_file(self, elm_id, context_str) :

		#idから完全名称を生成する
		invert_str = elm_id[::-1]
		invert_str = invert_str.replace('_', ':', 1)

		elm_full_name = invert_str[::-1]

		#xbrlファイルを調査する
		select_str = elm_full_name.replace(':', '|') + "[contextRef='" + context_str + "']"
		data_elm = self.__xbrl_instance_file_soup.select_one(select_str)

		return_data = None
		if data_elm != None and data_elm.get_text() != '':

			return_data = data_elm.get_text()

		else :
			return_data = '-'

		return return_data


	def get_context_list(self):

		return copy.deepcopy(self.__context_list)

	def show_context_list(self):

		for context in self.__context_list :
			print( str(context) )


	#コンテキストを選別する
	@staticmethod
	def select_context_by_axis(context_list, axis_id_list):

		delete_list = list()
		for context in context_list :

			if not context.is_match_by_axis(axis_id_list) :

				delete_list.append(context)


		for delete_context in delete_list :

			context_list.remove(delete_context)

	@staticmethod
	def select_context_by_member(context_list, axis_id, member_id, dimension_default_flag):

		delete_list = list()
		for context in context_list :

			if not context.is_match_by_member(axis_id, member_id, dimension_default_flag) :

				delete_list.append(context)


		for delete_context in delete_list :

			context_list.remove(delete_context)

	@staticmethod
	def select_context_by_period_type(context_list, period_type):

		delete_list = list()
		for context in context_list :

			if not context.is_match_by_period_type(period_type) :

				delete_list.append(context)


		for delete_context in delete_list :

			context_list.remove(delete_context)

#コンテキスト
class Context() :

	def __init__(self, name, period_type, instant_date, start_date, end_date, scenario) :

		self.__name = name
		self.__period_type = period_type
		self.__instant_date = instant_date
		self.__start_date = start_date
		self.__end_date = end_date

		#シナリオ
		# axis -> member == ( axis, member )のlist
		self.__scenario = scenario

	def get_name(self) :
		return self.__name
	
	#コンテキストが軸にマッチしているか
	def is_match_by_axis(self, axis_id_list):

		#軸がない場合はシナリオ無しなら欲しいコンテキスト
		if axis_id_list == None or len(axis_id_list) == 0 :

			if len(self.__scenario) == 0 :

				return True

			else :

				return False

		#軸がある場合は、その軸以外の軸がなければ欲しいコンテキスト
		is_match = True
		for tuple in self.__scenario :

			scenario_axis_id = tuple[0]
			if scenario_axis_id not in axis_id_list :

				is_match = False
				break

		return is_match



	def is_match_by_member(self, axis_id, member_id, dimension_default_flag):

		#ディメンションデフォルトに対する処理
		#軸がシナリオに存在しないなら欲しいコンテキスト
		if dimension_default_flag == True :

			for tuple in self.__scenario :
			
				scenario_axis_id = tuple[0]

				if scenario_axis_id == axis_id :

					return False

			return True


		#ディメンションデフォルト以外に対する処理
		#指定された軸とメンバーの組が存在するなら欲しいコンテキスト
		for tuple in self.__scenario :

			scenario_axis_id = tuple[0]
			scenario_member_id = tuple[1]

			if scenario_axis_id == axis_id and scenario_member_id == member_id :

				return True

		return False


	def is_match_by_period_type(self, period_type):

		if self.__period_type == period_type :

			return True

		else :

			return False


	def __str__(self) :


		date_str = None
		if self.__period_type == 'instant' :

			date_str = self.__instant_date

		else :

			date_str = 'from ' + self.__start_date + ' to ' + self.__end_date


		axis_member_str_list = list()

		for axis_to_member_tuple in self.__scenario :

			axis_name = axis_to_member_tuple[0]
			member_name = axis_to_member_tuple[1]

			axis_member_str_list.append( axis_name + '->' + member_name)


		if len(axis_member_str_list) == 0 :

			axis_member_str_list.append('no scenario')


		return self.__name + ' ' + date_str + ' ' + ','.join(axis_member_str_list)


#インスタンス文書から取得したデータ
class XBRLData():

	def __init__(self, member_to_contextdict_dict) :

		self.__member_to_contextdict_dict = member_to_contextdict_dict


	def get_data_dimension(self) :

		member_id_list = self.__member_to_contextdict_dict.keys()

		if len(member_id_list) == 1 and list(member_id_list)[0] == 'no member' :

			return '1d'

		else :

			return '2d'


	def get_data(self) :

		if self.get_data_dimension() == '1d' :

			return self.__member_to_contextdict_dict['no member']

		else :

			return self.__member_to_contextdict_dict


