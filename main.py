import os
import subprocess
import requests
from subprocess import check_output
from git import Repo
from decouple import config


class PullRequest:

    def __init__(self):
        self.repository_path = "https://api.github.com/repos/go-gitea/gitea/releases/latest"
        self.latest_release = None
        self.last_saved = None
        self.sha1sum = None
        self.sha256sum = None
        self.md5sum = None
        self.webhook = None  # insert "webhook url address"
        self.repository = None
        self.username = config('username', default='')
        self.token = config('token', default='')
        self.remote = f"https://{self.username}:{self.token}@github.com/wkobiela/spksrc.git"

    def get_latest(self):
        self.latest_release = requests.get(f"{self.repository_path}").json()["tag_name"]
        return self.latest_release

    def read_version(self):
        if os.path.isfile(".version"):
            get_saved = [line.split() for line in open(".version", "r+")]
            self.last_saved = get_saved[0][0]
            return self.last_saved
        else:
            file = open(".version", "w")
            print(self.latest_release, file=file)
            print("DEBUG : No .version file. Creating and filling one... \t DONE".expandtabs(150))
            exit("DEBUG : First run finished. \t EXITING".expandtabs(150))

    def discord_notify(self):
        content = f"**NEW GITEA UPDATE!** \nRelease: {self.latest_release}."
        payload = {'username': 'GiteaBot', "content": {content}}
        try:
            requests.post(self.webhook, data=payload)
            print("DEBUG : Discord message sent successfully. \t DONE".expandtabs(150))
        except Exception as e:
            print(f"ERROR : Something went wrong while sending notification. Msg: {e}\t FAILED".expandtabs(150))
            pass

    @staticmethod
    def write_version(latest_release):
        if os.path.isfile(".version"):
            file = open(".version", "r+")
            file.seek(0)
            file.truncate()
            print(latest_release, file=file)
        else:
            exit("ERROR: Something in writing .version file function went wront. \t EXITING".expandtabs(150))

    def git_pull_and_checkout(self):
        if os.path.isdir("spksrc"):
            print("DEBUG : Repo already exists... \t PASS".expandtabs(150))
            pass
        else:

            print("DEBUG : Repo does not exist. Setting up... \t IN PROGRESS".expandtabs(150))
            # os.popen(f"git clone https://github.com/wkobiela/spksrc.git && cd spksrc && git remote add "
            #          f"upstream https://github.com/SynoCommunity/spksrc.git").read()
            Repo.clone_from(self.remote, f"{os.getcwd()}/spksrc")
            self.repository = Repo(f"{os.getcwd()}/spksrc")
            cmd1 = f"cd spksrc && git remote add " \
                   f"upstream https://github.com/SynoCommunity/spksrc.git"
            p1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            p1.communicate()
            print("DEBUG : Repo setting up...  \t DONE".expandtabs(150))

        print("DEBUG : Updating repository... \t IN PROGRESS".expandtabs(150))
        try:
            # INFO : Commented is for testing purposes
            # os.popen(f"cd spksrc && git restore . && git pull upstream master && git rebase upstream/master").read()
            # os.popen(f"cd spksrc && git checkout master && git pull upstream master && git rebase upstream/master "
            #          f"&& git checkout -b {self.latest_release}").read()
            # TODO : Check, if branch already exists (now it stays on master if branch exists)
            # cmd2 = f"cd spksrc && git checkout master && git pull upstream master && git rebase upstream/master " \
            #        f"&& git checkout -b {self.latest_release}"

            cmd2 = f"cd spksrc && git checkout master && git pull upstream master && git rebase upstream/master " \
                   f"&& git checkout -b test_branch"
            p2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, shell=True)
            p2.communicate()
            print("DEBUG : Repository updated successfully.  \t DONE".expandtabs(150))
        except Exception:
            print("ERROR : Something went wrong while updating repository. \t EXITING".expandtabs(150))


    def create_digests(self, hash_type):
        if os.path.isfile(f"{self.latest_release}.tar.gz"):
            digests = os.popen(f"{hash_type.lower()} {self.latest_release}.tar.gz").read()
            temp = digests.split()
            temp.reverse()
            temp[0] = f"gitea-{self.latest_release[1:]}.tar.gz"
            temp.insert(1, hash_type[:-3])
            return " ".join(temp)
        else:
            exit(f"ERROR: Package {self.latest_release}tar.gz doesn't exist. \t EXITING".expandtabs(150))

    def download_gitea_package(self):
        if os.path.isfile(f"{self.latest_release}.tar.gz"):
            print(f"DEBUG : File {self.latest_release}.tar.gz is already downloaded... \t PASS".expandtabs(150))
            pass
        else:
            print(f"DEBUG : Downloading package... \t IN PROGRESS".expandtabs(150))
            try:
                os.popen(f"wget https://github.com/go-gitea/gitea/archive/refs/tags/"
                         f"{self.latest_release}.tar.gz").read()
                print("DEBUG : Downloading package... \t DONE".expandtabs(150))
            except Exception:
                print("DEBUG : Something went wrong while downloading package. \t EXITING".expandtabs(150))
        try:
            print("DEBUG : Calculating checksums for digests... \t IN PROGRESS".expandtabs(150))
            self.sha1sum = self.create_digests("SHA1SUM")
            self.sha256sum = self.create_digests("SHA256SUM")
            self.md5sum = self.create_digests("MD5SUM")
            print("DEBUG : Calculating checksums for digests... \t DONE".expandtabs(150))
        except Exception:
            exit("ERROR: Getting checksums went wrong. \t EXITING".expandtabs(150))

    def update_digests_file(self):
        if os.path.isfile("spksrc/cross/gitea/digests"):
            file = open("spksrc/cross/gitea/digests", "r+")
            file.seek(0)
            file.truncate()
            file.write(f"{self.sha1sum}\n{self.sha256sum}\n{self.md5sum}\n")
            file.close()
            print("DEBUG : Updating cross/gitea/digests file... \t DONE".expandtabs(150))
        else:
            exit("ERROR : Something went wrong during cross/gitea/digests file update. \t EXITING".expandtabs(150))

    def update_cross_makefile(self):
        if os.path.isfile("spksrc/cross/gitea/Makefile"):
            with open("spksrc/cross/gitea/Makefile", "r+") as file:
                data = file.readlines()
            data[1] = f"PKG_VERS = {self.latest_release[1:]}\n"
            with open("spksrc/cross/gitea/Makefile", "w") as file:
                file.writelines(data)
            file.close()
            print("DEBUG : Updating cross/gitea/Makefile...  \t DONE".expandtabs(150))
        else:
            exit("ERROR : Something went wrong during cross/gitea/Makefile file update. \t EXITING".expandtabs(150))

    def update_gitea_makefile(self):
        if os.path.isfile("spksrc/spk/gitea/Makefile"):
            with open("spksrc/spk/gitea/Makefile", "r+") as file:
                data = file.readlines()
            file.close()
            data[1] = f"SPK_VERS = {self.latest_release[1:]}\n"
            revision = int(data[2][10:]) + 1
            data[2] = f"SPK_REV = {revision}\n"
            data[8] = f'''CHANGELOG = "1. Update to {self.latest_release}."\n'''
            with open("spksrc/spk/gitea/Makefile", "w") as file:
                file.writelines(data)
            file.close()
            print("DEBUG : Updating spk/gitea/Makefile...  \t DONE".expandtabs(150))
        else:
            exit("ERROR : Something went wrong during spk/gitea/Makefile file update \t EXITING".expandtabs(150))

    def commit_changes(self):
        try:
            self.repository.git.add(update=True)
            self.repository.index.commit(f"Update Gitea to {self.latest_release}")
            print("DEBUG : Committing changes... \t DONE".expandtabs(150))
        except Exception:
            exit("DEBUG : Something went wrong while committing changes. \t EXITING".expandtabs(150))

    def push_changes(self):
        try:
            origin = self.repository.remote(name="origin")
            self.repository.head.reference.set_tracking_branch(origin.refs.master).checkout()
            #origin.push(self.latest_release)
            origin.push("test_branch")
            print("DEBUG : Pushing changes... \t DONE".expandtabs(150))
        except Exception as e:
            print(f"EXCEPTION: {e}")
            exit("DEBUG : Something went wrong while pushing changes. \t EXITING".expandtabs(150))

    @staticmethod
    def cleanup(latest):
        if os.path.isfile(f"{latest}.tar.gz"):
            try:
                check_output(["rm", f"{latest}.tar.gz"])
                print(f"DEBUG : Removing {latest}.tar.gz from {os.getcwd()}... \t DONE".expandtabs(150))
            except subprocess.CalledProcessError:
                print(f"ERROR : Couldn't delete {latest}.tar.gz file. \t PASS".expandtabs(150))
                pass
        else:
            print("DEBUG : There is nothing to delete and nothing happens. \t PASS".expandtabs(150))
            pass

        # TODO: Uncomment git_pull_and_checkout operation 
        # TODO: Function to push commit to repo after changes was made
        # TODO: Function to create PR from wkobiela/spksrc to synocommunity/spksrc with correct template

    def run(self):
        if self.get_latest() != self.read_version():
            print(f"DEBUG : Newer version appeared: {self.latest_release}. Executing... \t IN PROGRESS".expandtabs(150))
            self.discord_notify()
            # self.write_version(self.latest_release)
            self.git_pull_and_checkout()
            self.download_gitea_package()
            self.update_digests_file()
            self.update_cross_makefile()
            self.update_gitea_makefile()
            self.commit_changes()
            self.push_changes()
            self.cleanup(self.latest_release)
            print("DEBUG : All jobs finished. \t EXITING".expandtabs(150))
            exit(0)
        else:
            print(f"DEBUG : No update. {self.last_saved} is still latest release... \t EXITING".expandtabs(150))
            exit(0)


gitea_update = PullRequest()
gitea_update.run()
