from requests import get, delete
from datetime import date, timedelta, datetime
from json import loads
from os import environ
from sys import argv


class NexusCleaner:

    # init from env var
    def __init__(self):

        try:
            self.NEXUS_ADRESS = environ.get('NEXUS_ADRESS')
            self.NEXUS_PORT = environ.get('NEXUS_PORT')
            self.USER_LOGIN = environ.get('USER_LOGIN')
            self.USER_PASSWORD = environ.get('USER_PASSWORD')
        except:
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
        search_url = '{0}:{1}/service/rest/beta/search'.format(self.NEXUS_ADRESS, self.NEXUS_PORT)
        try:
            response = get(search_url, auth=(self.USER_LOGIN, self.USER_PASSWORD), params=params)
        except:
            print('Incorrect adress / Not authenticated / Problem with Nexus server')
            raise SystemExit
        response = response.json()
        images = response['items']
        self.my_images = []
        for image in images:
            ImageUrl = image['assets'][0]['downloadUrl']
            try:
                response = get(ImageUrl, auth=(self.USER_LOGIN, self.USER_PASSWORD))
            except:
                print('Problem with Nexus server | Image get request')
                raise SystemExit
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
            response = delete(DelUrl, auth=(self.USER_LOGIN, self.USER_PASSWORD), headers=headers)
        except:
            print('Problem with Nexus server | Image delete request')
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

if __name__ == "__main__":

    flag_list = argv[1:]
    my_flags = ['-k', '-d', '-r', '-i', '-t', '--all-repositories', '--all-images']
    if '--all-repositories' in flag_list:
        RepoName = ''
        flag_list.remove('--all-repositories')
        my_flags.remove('-r')
        my_flags.remove('--all-repositories')
    if '--all-images' in flag_list:
        ImageName = ''
        flag_list.remove('--all-images')
        my_flags.remove('-i')
        my_flags.remove('--all-images')
    flag_dict = {}
    for flag_i in range(0, len(flag_list), 2):
        if flag_list[flag_i] not in my_flags:
            print(('incorrect flag: {0}'.format(flag_list[flag_i])))
            raise SystemExit
        else:
            flag_dict[flag_list[flag_i]] = flag_list[flag_i + 1]
    if '-r' not in flag_dict and 'RepoName' not in globals():
        print('Miss repo (-r) flag: use --all-repositories to clean all repositories')
        raise SystemExit
    if '-i' not in flag_dict and 'ImageName' not in globals():
        print('Miss image (-i) flag: use --all-images to clean all images')
        raise SystemExit
    Keep = 5 if '-k' not in flag_dict else flag_dict['-k']
    Days = 10 if '-d' not in flag_dict else flag_dict['-d']
    ImageVersion = '' if '-t' not in flag_dict else flag_dict['-t']
    if '-r' in flag_dict:
        RepoName = flag_dict['-r']
    if '-i' in flag_dict:
        ImageName = flag_dict['-i']

    nexus = NexusCleaner()
    deleted_list = nexus.clean_old_images(Keep=int(Keep), Days=int(Days), RepoName=RepoName, ImageName=ImageName, ImageVersion=ImageVersion)
    if deleted_list:
        for image in deleted_list:
            print(('REPOSITORY: {0} | DELETED: {1}:{2}'.format(image['RepoName'], image['ImageName'], image['ImageVersion'])))
    else:
        print('No images in delete query')