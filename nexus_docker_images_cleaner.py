from requests import get, delete
from datetime import date, timedelta, datetime
from json import loads
from os import environ
from sys import argv


class NexusCleaner:

    # init from env var
    # refactor this later (get rid of if)
    def __init__(self):
        self.NEXUS_ADDRESS = environ.get('NEXUS_ADDRESS')
        self.NEXUS_PORT = environ.get('NEXUS_PORT')
        self.NEXUS_USER_LOGIN = environ.get('NEXUS_USER_LOGIN')
        self.NEXUS_USER_PASSWORD = environ.get('NEXUS_USER_PASSWORD')
        if self.NEXUS_ADDRESS is None or self.NEXUS_PORT is None or self.NEXUS_USER_LOGIN is None or self.NEXUS_USER_PASSWORD is None:
            print('Environment variables not set')
            raise SystemExit

    # find all docker images by repo, name, tag
    # creating and appending my_images
    def _check_nexus_images(self, RepoName='', ImageName='', ImageVersion=''):
        params = {'format': 'docker'}
        if RepoName:
            params['repository'] = RepoName
        if ImageName:
            params['name'] = ImageName
        if ImageVersion:
            params['version'] = ImageVersion
        search_url = '{0}:{1}/service/rest/beta/search'.format(self.NEXUS_ADDRESS, self.NEXUS_PORT)
        try:
            response = get(search_url, auth=(self.NEXUS_USER_LOGIN, self.NEXUS_USER_PASSWORD), params=params)          
        except Exception as error:
            print('Problem with connect to Nexus:')
            print(error)
            raise SystemExit
        try:    
            response = response.json()
        except Exception as error:
            print('Problem with json response from Nexus:')
            print(error)
            raise SystemExit
            
        images = response['items']
        self.my_images = []
        for image in images:
            ImageUrl = image['assets'][0]['downloadUrl']
            response = get(ImageUrl, auth=(self.NEXUS_USER_LOGIN, self.NEXUS_USER_PASSWORD))
            response = response.json()
            tmp_str = response['history'][0]['v1Compatibility']
            tmp_json = loads(tmp_str)
            CreateDate = tmp_json['created']
            ImageSha = image['assets'][0]['checksum']['sha256']
            RepoName = image['repository']
            ImageName = image['name']
            ImageVersion = image['version']
            self.my_images.append({
                'ImageUrl': ImageUrl,
                'CreateDate': CreateDate,
                'ImageSha': ImageSha,
                'RepoName': RepoName,
                'ImageName': ImageName,
                'ImageVersion': ImageVersion,
                })

    # del image by url
    # return request status code
    def _delete_image(self, ImageUrl, ImageSha):
        digest = 'sha256:' + ImageSha
        headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
        tmp_pos = ImageUrl.rfind('/')
        DelUrl = ImageUrl[:tmp_pos + 1] + digest
        try:
            response = delete(DelUrl, auth=(self.NEXUS_USER_LOGIN, self.NEXUS_USER_PASSWORD), headers=headers)
        except:
            print('Problem with Nexus server')
            raise SystemExit
        return response.status_code

    # prepare my_images to delete without keep images
    def _check_image_keep(self, Keep):
        if Keep < len(self.my_images):
            self.my_images = sorted(self.my_images, key=lambda elem: elem['CreateDate'], reverse=True)
            self.my_images = self.my_images[Keep:]

    # prepare del_images to usage without fresh images
    def _check_image_date(self, Days):
        OldDate = date.today() - timedelta(days=Days)
        self.del_images = []
        for image in self.my_images:
            ImageDate = image['CreateDate'][:10]
            ImageDate = datetime.strptime(ImageDate, "%Y-%m-%d").date()
            if ImageDate < OldDate:
                self.del_images.append(image)

    # clean all old images (by day, by repo, by image name, by tag)
    # return list of dicts of deleted images
    def clean_old_images(self, Keep=0, Days=0, RepoName='', ImageName='', ImageVersion=''):
        self._check_nexus_images(RepoName=RepoName, ImageName=ImageName, ImageVersion=ImageVersion)
        self._check_image_keep(Keep)
        self._check_image_date(Days)
        for image in self.del_images:
            image['DeleteCode'] = self._delete_image(image['ImageUrl'], image['ImageSha'])
        return self.del_images


# goofy flag parser (maybe try to refactoring this to func-style)
# return needed-parameters list
def nexus_cleaner_flag_parse(flag_list):
    if '-h' in flag_list:
        print(
    '''
    usage:\tpython3 nexus_docker_images_cleaner.py [options]

    Options and arguments:
    -d\t\t\t:[int] Days count after which image is deleted. (!) Can't be used with '-k' option.
    -h\t\t\t:[] Help.
    -i [REQUIRED]\t:[str] Image name. If you want to work with all images use '--all-images' option.
    -k\t\t\t:[int] Number of latest images to keep. (!) Can't be used with '-d' option.
    -r [REQUIRED]\t:[str] Repository name. If you want to work with all repositories use '--all-repositories' option.
    -t\t\t\t:[str] Tag name (delete all by default).

    Confirming options:
    --all-images\t:[] Use to clean all images instead '-i'.
    --all-repositories\t:[] Use to clean all repositories instead '-r'.
    ''')
        raise SystemExit
    flag_map = ['-k', '-d', '-r', '-i', '-t', '-h', '--all-repositories', '--all-images']
    if '--all-repositories' in flag_list:
        RepoName = ''
        flag_list.remove('--all-repositories')
        flag_map.remove('-r')
        flag_map.remove('--all-repositories')
    if '--all-images' in flag_list:
        ImageName = ''
        flag_list.remove('--all-images')
        flag_map.remove('-i')
        flag_map.remove('--all-images')
    flag_dict = {}
    for flag_i in range(0, len(flag_list), 2):
        if flag_list[flag_i] not in flag_map:
            print(('incorrect flag: {0}'.format(flag_list[flag_i])))
            raise SystemExit
        else:
            flag_dict[flag_list[flag_i]] = flag_list[flag_i + 1]
    if '-r' not in flag_dict and 'RepoName' not in locals():
        print('Miss repo (-r) flag: use --all-repositories to clean all repositories')
        raise SystemExit
    if '-i' not in flag_dict and 'ImageName' not in locals():
        print('Miss image (-i) flag: use --all-images to clean all images')
        raise SystemExit
    if '-d' in flag_dict and '-k' in flag_dict:
        print("Use of incompatible options '-d' and '-k'")
        raise SystemExit
    elif '-d' in flag_dict:
        Days = flag_dict['-d']
        try:
            int(Days)
        except:
            print('Incorrect data type: -d')
        Keep = 0
    elif '-k' in flag_dict:
        Keep = flag_dict['-k']
        try:
            int(Keep)
        except:
            print('Incorrect data type: -k')
        Days = 0
    else:
        Keep = 0
        Days = 0
    ImageVersion = '' if '-t' not in flag_dict else flag_dict['-t']
    if '-r' in flag_dict:
        RepoName = flag_dict['-r']
    if '-i' in flag_dict:
        ImageName = flag_dict['-i']
    return [Keep, Days, RepoName, ImageName, ImageVersion]


if __name__ == "__main__":
    flag_list = nexus_cleaner_flag_parse(argv[1:])
    nexus = NexusCleaner()
    deleted_list = nexus.clean_old_images(
        Keep=int(flag_list[0]),
        Days=int(flag_list[1]),
        RepoName=flag_list[2],
        ImageName=flag_list[3],
        ImageVersion=flag_list[4])
    if deleted_list:
        for image in deleted_list:
            print(('REPOSITORY: {0} | DELETED: {1}:{2}'.format(image['RepoName'], image['ImageName'], image['ImageVersion'])))
    else:
        print('No images in delete query')
