from requests import get, delete
from datetime import date, timedelta, datetime
from json import loads
from os import environ
from sys import argv
from argparse import ArgumentParser


# main class
class NexusCleaner:

    # init from env var
    # refactor this later (get rid of if)
    def __init__(self):
        self.NEXUS_ADDRESS = environ.get('NEXUS_ADDRESS')
        self.NEXUS_PORT = environ.get('NEXUS_PORT')
        self.NEXUS_USER_LOGIN = environ.get('NEXUS_USER_LOGIN')
        self.NEXUS_USER_PASSWORD = environ.get('NEXUS_USER_PASSWORD')
        if (self.NEXUS_ADDRESS is None or 
            self.NEXUS_PORT is None or 
            self.NEXUS_USER_LOGIN is None or 
            self.NEXUS_USER_PASSWORD is None):
            print('Environment variables not set')
            raise SystemExit

    # del image by url
    # return request status code
    def _delete_image(self, ImageUrl, ImageSha):
        digest = 'sha256:' + ImageSha
        headers = {
        'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
        tmp_pos = ImageUrl.rfind('/')
        DelUrl = ImageUrl[:tmp_pos + 1] + digest
        try:
            response = delete(DelUrl, auth=(
                self.NEXUS_USER_LOGIN, 
                self.NEXUS_USER_PASSWORD), 
            headers=headers)
        except:
            print('Problem with Nexus server')
            raise SystemExit
        return response.status_code

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
        search_url = '{0}:{1}/service/rest/beta/search'.format(
            self.NEXUS_ADDRESS, 
            self.NEXUS_PORT)
        try:
            response = get(search_url, auth=(
                self.NEXUS_USER_LOGIN, 
                self.NEXUS_USER_PASSWORD), 
            params=params)          
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

            # very strange REST record - need investigate
            try:
                ImageUrl = image['assets'][0]['downloadUrl']
            except:
                continue

            response = get(ImageUrl, auth=(
                self.NEXUS_USER_LOGIN, 
                self.NEXUS_USER_PASSWORD))
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

    # prepare my_images to delete without keep images
    def _check_image_keep(self, Keep):

        # check this bug(?)
        if Keep < 0: 
            print('Incorrect type')
            raise SystemExit

        if Keep <= len(self.my_images):
            self.my_images = sorted(
                self.my_images, 
                key=lambda elem: elem['CreateDate'], 
                reverse=True)
            self.my_images = self.my_images[Keep:]
        elif Keep > len(self.my_images):
            print('All images keeps')
            raise SystemExit

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
    def clean_old_images(
        self, 
        Keep=0, 
        Days=0, 
        RepoName='', 
        ImageName='', 
        ImageVersion=''):
        self._check_nexus_images(
            RepoName=RepoName, 
            ImageName=ImageName, 
            ImageVersion=ImageVersion)
        self._check_image_keep(Keep)
        self._check_image_date(Days)
        for image in self.del_images:
            image['DeleteCode'] = self._delete_image(
                image['ImageUrl'], 
                image['ImageSha'])
        return self.del_images

# main function
def main():

        def flag_parser():
            # my parser check
            def simple_parser_check(my_args_dict):
                def parser_cjeck_error_raiser():
                    print('''Significant errors in ArgumentParser
                     - contact the maintainer.''')
                    raise SystemExit
                if (my_args_dict['i'] == ''  and
                    my_args_dict['all_images'] == False):
                    parser_cjeck_error_raiser()
                elif (my_args_dict['r'] == '' and
                    my_args_dict['all-repositories'] == False):
                    parser_cjeck_error_raiser()


            # create parser
            nexus_cleaner_parser = ArgumentParser(
                prog='python3 nexus_docker_images_cleaner.py', 
                description='''Delete docker images in Nexus Repository Manager 3
                Requires environment variables:
                    NEXUS_ADDRESS, 
                    NEXUS_PORT, 
                    NEXUS_USER_LOGIN, 
                    NEXUS_USER_PASSWORD.
                ''')

            # create repo group flags 
            repos_group = nexus_cleaner_parser.add_mutually_exclusive_group(
                required=True)
            repos_group.add_argument(
                '-r', 
                metavar='str_repo_name', 
                type=str, 
                default='',
                help='''Repository name. 
                If you want to work with all repositories 
                use '--all-repositories' option.''')
            repos_group.add_argument(
                '--all-repositories', 
                action='store_true',
                help="Use to clean all repositories instead '-r'.")

            # create image group flags 
            images_group = nexus_cleaner_parser.add_mutually_exclusive_group(
                required=True)
            images_group.add_argument(
                '-i', 
                metavar='str_image_name', 
                type=str, 
                default='',
                help='''Image name. 
                If you want to work with all images use '--all-images' option.''')
            images_group.add_argument(
                '--all-images', 
                action='store_true',
                help="Use to clean all images instead '-i'.")

            # create keed and day group flags 
            keep_day_group = nexus_cleaner_parser.add_mutually_exclusive_group()
            keep_day_group.add_argument(
                '-d', 
                default=0,
                metavar='int_days', 
                type=int,
                help='''Days count after which image is deleted (0 by default). 
                (!) Can't be used with '-k' option.''')
            keep_day_group.add_argument(
                '-k', 
                default=0, 
                metavar='int_keep', 
                type=int,
                help='''Number of latest images to keep (0 by default). 
                (!) Can't be used with '-d' option.''')

            # create version flag 
            nexus_cleaner_parser.add_argument(
                '-t', 
                metavar='str_image_version', 
                default='', 
                type=str, 
                help="[str] Tag name (delete all by default).")

            my_args_dict = vars(nexus_cleaner_parser.parse_args())
            simple_parser_check(my_args_dict)
            return my_args_dict     
        my_args_dict = flag_parser()        
        nexus = NexusCleaner()
        deleted_list = nexus.clean_old_images(
            Keep=my_args_dict['k'],
            Days=my_args_dict['d'],
            RepoName=my_args_dict['r'],
            ImageName=my_args_dict['i'],
            ImageVersion=my_args_dict['t'])
        if deleted_list:
            for image in deleted_list:
                print(('REPOSITORY: {0} | DELETED: {1}:{2}'.format(
                    image['RepoName'], 
                    image['ImageName'], 
                    image['ImageVersion'])))
        else:
            print('No images in delete query')

if __name__ == "__main__":
    main()
