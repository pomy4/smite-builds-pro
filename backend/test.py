import pickle
import models

def pickle_test():
    with open('test.p', 'rb') as f:
        builds = pickle.load(f)
        for build in builds:
            print(build)

# pickle_test()
with open('test.p', 'rb') as f:
    builds = pickle.load(f)
    models.db.connect()
    models.add_builds(builds)
    models.db.close()
