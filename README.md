# Project context

I needed to run some automated backups on my home server, covering a long period as it may take me a while to realize that a rollback would be necessary, and with reduced disk usage.

An elegant way to do this would be to keep a large amount of backups of recent states, and keep less as we go back in history. This way we could restore a backup from a very specific period if we quickly realize that there is a problem, while leaving the possibility of choosing a much older version if necessary, even if it is less accurate in time.

I'm quite a fanatic of continuous rules, it seems to me quite dirty to choose a sequence of arbitrary delays for which the program chooses to change its behavior towards the saved backups. My program will evaluate the deletion of backups according to a logarithmic law adapting to the present backups.

This script is adapted from [Neil Fraser and Christopher Allen logarithmic backup algorithm](https://neil.fraser.name/software/backup/). The exact problem solved by this algorithm is well defined by its authors (their website includes a simulator that gives a pretty strong intuition on the precise behavior of this algorithm):
> A common problem when archiving backups is how to (at any given time) have a backup from a day ago, a backup from two days ago, a backup from from four days ago, and so on. Backups may be taken daily, but due to storage constraints most must be deleted. There should be more backups retained of recent history than ancient history. Figuring out which backups to keep and which to delete is tricky.
>
> There are [many backup rotation schemes](https://en.wikipedia.org/wiki/Backup_rotation_scheme), such as "Grandfather, Father, Son", or the more elegant "Tower of Hanoi". However, while these systems are simple and produce good results, they don't recover well when there are holes in the backup cycles (resulting from downtime, data-loss, or other factors). These strategies are also wasteful of available media before they hit their maximum saturation point (e.g. if there is room to store 10 backups, then at the end of 10 days all 10 daily backups should be available). Furthermore, they don't scale once the media is fully used, requiring either the oldest history to be dropped or additional media to be added (albeit at a logarithmically decreasing rate).
>
> The logarithmic strategy presented here is based on the premise that the available media will be maximally utilized, but will not be expected to grow. This strategy also accommodates irregular backups and changes to the amount of media available.

# Script usage

This command will create a .tar archive of the _\<source_directory\>_ and will save it in the _\<backup_directory\>_:

```
python3 logarithmicBackup.py -s <source_directory> -b <backup_directory> <more options>
```

| Option                              | Usage                                                                                                                | python type <br> _default value_ |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------| -------------------------------- |
| __-s <br> --src_dir__               | __source directory path<span style="color:red">*</span>__ <br> _the content of this directory will be archived_      | __str__                          |
| __-b <br> --bkp_dir__               | __destination directory path<span style="color:red">*</span>__ <br> _this directory will contains backuped archives_ | __str__                          |
| -p <br> --bkp_prefix                | backup name prefix <br> _used to make several backups coexist in the same directory_                                 | str <br> _"backup"_              |
| -i <br> --expected_bkp_interval_sec | expected time between regular backup events [seconds]                                                                | int <br> _3600 # 1 day_          |
| -m <br> --max_bkp_kept              | maximum amount of backups kept                                                                                       | int <br> _14_                    |
| -o <br> --outdated_bkp_sec          | time for which a backup is outdated [seconds] <br> _an outated backup will be deleted first if space is needed before any other evaluation_ | int <br> _2457600 # 2 years_ |
| -c <br> --compress                  | compress backups <br> _makes .tar.gz compressed files instead of .tar files_                                         | bool <br> _False_                |
| -h <br> --help                      | show the help on the go                                                                                              | _no argument_                    |

# Typical implementation

This script is designed to be integrated into a cron job, one call for each backup.

Use case example with my crontab:
```
# weekly backup
10 5 * * 3 rsync -r --delete --ignore-existing /backup/ /mnt/raid/cronBackup

# daily backups
10 4 * * * python3 /tools/logarithmicBackup.py -s /opt/duckdns -b /backup/duckdns -i 86400 -c true
15 4 * * * python3 /tools/logarithmicBackup.py -s /opt/jellyfin -b /backup/jellyfin -i 86400 -c true
20 4 * * * python3 /tools/logarithmicBackup.py -s /opt/caddy -b /backup/caddy -i 86400 -c true
25 4 * * * python3 /tools/logarithmicBackup.py -s /opt/smb -b /backup/smb -i 86400 -c true
30 4 * * * python3 /tools/logarithmicBackup.py -s /opt/wordpress -b /backup/wordpress -i 86400 -c true

# hourly backups
35 * * * * python3 /tools/logarithmicBackup.py -s /opt/minecraft -b /backup/minecraft -c true
45 * * * * python3 /tools/logarithmicBackup.py -s /opt/satisfactory -b /backup/satisfactory -c true
55 * * * * python3 /tools/logarithmicBackup.py -s /opt/factorio -b /backup/factorio -c true
05 * * * * python3 /tools/logarithmicBackup.py -s /opt/zomboid -b /backup/zomboid -c true

```

This particular crontab will do some daily and some hourly compressed backups from _/opt/\<service_name\>_ to _/backup/\<service_name\>_ (these two directories are on my system SSD). Then once a week, a rsync backup will be performed in a second volume just in case of a hardware failure.
