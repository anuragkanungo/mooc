from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import os
from track.management.tracked_command import TrackedCommand
from django.conf import settings

class Command(TrackedCommand):
    help = """
    Initialize Institute Folders
    """

    def handle(self, *args, **options):
        insti_id = args[0]
        if not insti_id:
            raise CommandError("Plese provide institute id")

        try:
            path =  str(settings.REPO_ROOT) + "/syncing/institute" + str(insti_id)
            os.mkdir(path)
        except  OSError:
            print "Already Exists"
