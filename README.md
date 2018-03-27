# nexus_docker_images_cleaner
Delete Nexus OSS Docker images by flags.


Requires environment variables:

NEXUS_ADDRESS    
NEXUS_PORT      
NEXUS_USER_LOGIN      
NEXUS_USER_PASSWORD   


    usage: python3 nexus_docker_images_cleaner.py   [-h]
                                                    (-r str_repo_name | --all-repositories)
                                                    (-i str_image_name | --all-images)
                                                    [-d int_days | -k int_keep]
                                                    [-t str_image_version]

