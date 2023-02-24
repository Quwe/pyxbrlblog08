import os
import glob
from .XBRLError import XBRLAnalysisError

class XBRLPath() :

	def __init__(self, xbrl_dir_path) :


		xbrl_files = glob.glob( os.path.join(xbrl_dir_path, 'XBRL' + os.sep + 'PublicDoc' + os.sep + '*.xbrl') )

		if len(xbrl_files) != 1 :

			raise XBRLAnalysisError('発見できたxbrlファイルの数が想定と異なります:' + str(len(xbrl_files)) )


		instance_file_path = xbrl_files[0]

		local_xbrl_dir_path = os.path.dirname(instance_file_path)
		local_xbrl_basename = os.path.basename(instance_file_path).replace('.xbrl', '')


		local_xsd_name = local_xbrl_basename + '.xsd'
		local_lab_name = local_xbrl_basename + '_lab.xml'
		local_def_name = local_xbrl_basename + '_def.xml'
		local_pre_name = local_xbrl_basename + '_pre.xml'
		local_xbrl_name = local_xbrl_basename + '.xbrl'

		self.__xsd_file_path = os.path.join(local_xbrl_dir_path, local_xsd_name)
		self.__lab_file_path = os.path.join(local_xbrl_dir_path, local_lab_name)
		self.__xbrl_file_path = os.path.join(local_xbrl_dir_path, local_xbrl_name)
		self.__def_linkbase_file_path = os.path.join(local_xbrl_dir_path, local_def_name)
		self.__pre_linkbase_file_path = os.path.join(local_xbrl_dir_path, local_pre_name)

		self.__xbrl_dir_path = local_xbrl_dir_path



	def get_xbrl_dir_path(self):
		return self.__xbrl_dir_path

	def get_xbrl_file_path(self):
		return self.__xbrl_file_path

	def get_xsd_file_path(self) :
		return self.__xsd_file_path

	def get_lab_file_path(self) :
		return self.__lab_file_path

	def get_pre_file_path(self) :
		return self.__pre_linkbase_file_path

	def get_def_file_path(self) :
		return self.__def_linkbase_file_path


def get_xbrl_dir_path() :

	return '.' + os.sep + 'xbrl'


def get_xbrl_file_path(doc_id) :


	return os.path.join( get_xbrl_dir_path(), doc_id + '.zip' )


def get_working_dir_path() :

	return '.' + os.sep + 'working'
