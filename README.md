# nexus_docker_images_cleaner
Delete Nexus OSS Docker images by flags.


Requires environment variables:

NEXUS_ADRESS    
NEXUS_PORT      
USER_LOGIN      
USER_PASSWORD   


    usage:      python3 nexus_docker_images_cleaner.py [options]

    Options and arguments:
    -d                  :[int] Days count after which image is deleted (10 by default). (!) Can't be used with '-k' option.
    -h                  :[] Help.
    -i [REQUIRED]       :[str] Image name. If you want to work with all images use '--all-images' option.
    -k                  :[int] Number of latest images to keep (5 by default). (!) Can't be used with '-d' option.
    -r [REQUIRED]       :[str] Repository name. If you want to work with all repositories use '--all-repositories' option.
    -t                  :[str] Tag name (delete all by default).

    Confirming options:
    --all-images        :[] Use to clean all images instead '-i'.
    --all-repositories  :[] Use to clean all repositories instead '-r'.

