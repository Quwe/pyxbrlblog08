import os
import glob
import shutil
import logging
import libxbrl


#65期の竹本容器の有報

#表示リンクベースファイルから有報の構造を読み込む
yuho_tree = libxbrl.XBRLStructureTree(libxbrl.XBRLPath('.\\S10079H3'))

for rol_str in yuho_tree.get_rol_list() :
	print(rol_str)



#とりあえず損益計算書を読み込む
rol_str = 'rol_StatementOfIncome'
#スキーマファイルの読み込み
yuho_tree.read_xsd_file(rol_str)

#日本語名称の読み込み
yuho_tree.read_jp_lab_file(rol_str)

#定義リンクベースファイルからディメンションデフォルトを読み込み
def_tree = libxbrl.XBRLDefinitionLinkBaseTree(libxbrl.XBRLPath('.\\S10079H3'))
yuho_tree.set_dimension_default(def_tree, rol_str)



#インスタンス文書からデータを読み込む
xbrl_instance_file_analyzer = libxbrl.XBRLInstanceFileAnalysis(libxbrl.XBRLPath('.\\S10079H3'))
yuho_tree.read_instance_data(rol_str, xbrl_instance_file_analyzer)

#構造を表示
yuho_tree.show_tree(rol_str)


#連結損益計算書の最新年度のデータをcsv形式で出力する
#1Dデータの場合
yuho_tree.set_walking_root(yuho_tree.search_node(rol_str))
for node in yuho_tree :

	if node.get_usage() != 'number' :
		continue

	if node.get_xbrl_data().get_data_dimension() != '1d' :

		raise libxbrl.XBRLAnalysisError('データの次元数が想定と異なります')


	#数値データの親文字列を取得する
	#財務諸表の数値データの親は必ずline_itemとなるため
	parent_str_list = list()
	current_node = node.get_parent()
	while current_node != None :

		parent_str_list.append(current_node.get_jp_label())

		if current_node.get_usage() == 'line_items' :

			break

		current_node = current_node.get_parent()

	parent_str_list.reverse()

	parent_str = ' '.join(parent_str_list)

	context_to_data_dict = node.get_xbrl_data().get_data()

	year_str = None
	if node.get_preferred_label() == 'http://www.xbrl.org/2003/role/periodStartLabel' :

		year_str = 'Prior1Year'

	else :

		year_str = 'CurrentYear'


	context_str = None
	for key_str in context_to_data_dict.keys() :

		if key_str.startswith(year_str) :

			context_str = key_str

	if context_str == None :

		raise libxbrl.XBRLAnalysisError('コンテキストを取得できない')


	print(parent_str + ',' + node.get_jp_label() + ',' + context_to_data_dict[context_str])



#株主資本等計算書を読み込む
rol_str = 'rol_StatementOfChangesInEquity'
#スキーマファイルの読み込み
yuho_tree.read_xsd_file(rol_str)

#日本語名称の読み込み
yuho_tree.read_jp_lab_file(rol_str)

#定義リンクベースファイルからディメンションデフォルトを読み込み
yuho_tree.set_dimension_default(def_tree, rol_str)

#インスタンス文書からデータを読み込む
yuho_tree.read_instance_data(rol_str, xbrl_instance_file_analyzer)

#構造を表示
yuho_tree.show_tree(rol_str)




#株主資本等変動計算書の最新年度のデータをcsv形式で出力する
#2Dデータの場合

#列方向の軸を取得する
table_structure_dict = yuho_tree.get_table_structure_dict(rol_str)
col_axis_member_list = None
for axis_id in table_structure_dict.keys() :

	#連結or単体軸は読み飛ばす
	if axis_id == 'jppfs_cor_ConsolidatedOrNonConsolidatedAxis' :

		continue

	col_axis_member_list = table_structure_dict[axis_id]

	break

col_member_jp_label_list = list()
for member in col_axis_member_list :
	col_member_jp_label_list.append(member.get_jp_label())

print('要素の親,要素名,' + ','.join(col_member_jp_label_list))

yuho_tree.set_walking_root(yuho_tree.search_node(rol_str))
for node in yuho_tree :

	if node.get_usage() != 'number' :
		continue

	if node.get_xbrl_data().get_data_dimension() != '2d' :

		raise libxbrl.XBRLAnalysisError('データの次元数が想定と異なります')


	#数値データの親文字列を取得する
	#財務諸表の数値データの親は必ずline_itemとなるため
	parent_str_list = list()
	current_node = node.get_parent()
	while current_node != None :

		parent_str_list.append(current_node.get_jp_label())

		if current_node.get_usage() == 'line_items' :

			break

		current_node = current_node.get_parent()

	parent_str_list.reverse()

	parent_str = ' '.join(parent_str_list)



	member_to_contextdict_dict = node.get_xbrl_data().get_data()



	year_str = None
	if node.get_preferred_label() == 'http://www.xbrl.org/2003/role/periodStartLabel' :

		year_str = 'Prior1Year'

	else :

		year_str = 'CurrentYear'


	#メンバー毎のデータを取得
	data_list = list()
	for member in col_axis_member_list :

		member_id = member.get_id()
		context_to_data_dict = member_to_contextdict_dict[member_id]

		#コンテキストが存在しないなら、データも取れない
		if len(context_to_data_dict.keys()) == 0 :

			data_list.append('-')
			continue

		context_str = None
		for key_str in context_to_data_dict.keys() :

			if key_str.startswith(year_str) :

				context_str = key_str
				break

		
		if context_str == None :

			raise libxbrl.XBRLAnalysisError('コンテキストを取得できない')

		data_list.append(context_to_data_dict[context_str])

	print(parent_str + ',' + node.get_jp_label() + ',' + ','.join(data_list))

