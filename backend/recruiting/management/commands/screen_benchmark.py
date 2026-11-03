"""
python manage.py screen_benchmark --job 1

Runs the same screening twice, sequential and threaded, and prints the speed-up.
Great to demo live in an interview when asked about multithreading.
"""
from django.core.management.base import BaseCommand, CommandError

from recruiting.models import Job
from recruiting.screening import BulkScreener


class Command(BaseCommand):
    help = "Compare sequential vs multithreaded screening for one job."

    def add_arguments(self, parser):
        parser.add_argument("--job", type=int, help="Job id (defaults to the first job)")
        parser.add_argument("--workers", type=int, default=8)

    def handle(self, *args, **opts):
        job = Job.objects.filter(pk=opts["job"]).first() if opts["job"] else Job.objects.first()
        if job is None:
            raise CommandError("No job found. Run `python manage.py seed_demo` first.")

        apps = job.applications.select_related("candidate", "job")
        n = apps.count()
        screener = BulkScreener(max_workers=opts["workers"])

        self.stdout.write(f"Screening {n} applications for '{job.title}'...")
        seq = screener.run(apps, sequential=True)
        self.stdout.write(f"  sequential : {seq.elapsed_ms:>6} ms  (1 thread)")
        par = screener.run(apps)
        self.stdout.write(f"  threaded   : {par.elapsed_ms:>6} ms  ({par.workers} threads)")
        if par.elapsed_ms:
            self.stdout.write(self.style.SUCCESS(f"  speed-up   : {seq.elapsed_ms / par.elapsed_ms:.1f}x"))
