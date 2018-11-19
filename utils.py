import sys, time

class ProgressBar:
    def __init__(self, count = 0, total = 0, width = 50):
        self.count = count
        self.total = total
        self.width = width

    def update(self):
        self.count += 1
        progress = int(self.width * self.count / self.total)
        sys.stdout.write('=' * progress + '-' * (self.width - progress)+" "*10)
        sys.stdout.write('[{0}/{1}] '.format(self.count, self.total)+'\r')
        sys.stdout.flush()
        if self.count==self.total:
            sys.stdout.write('\n')
            sys.stdout.flush()

def retry(tries=5,interval=5):
    def wrapper(fun):
        def retry_calls(*args, **kwargs):
            if tries:
                for _ in range(tries):
                    try:
                        return fun(*args, **kwargs)
                    except Exception:
                        time.sleep(interval)
                    else:
                        break
            else:
                while True:
                    try:
                        return fun(*args, **kwargs)
                    except Exception:
                        time.sleep(interval)
                    else:
                        break
        return retry_calls
    return wrapper
