# cci

Command line interface for [cottoncandy](https://gallantlab.org/cottoncandy/).
## Usage

The bucket is the first argument of every bucket-scoped command:

```
cci                                # lsdir "/" on your configured default_bucket
cci lsdir mybucket sub/            # list the immediate contents of "sub/"
cci ls mybucket "sub/*.txt"        # list objects matching a pattern
cci du mybucket                    # total size of the bucket
cci download mybucket notes.txt    # download an object
cci list                           # list available buckets (s3 only)
```

Credentials, the default bucket, and the endpoint come from your cottoncandy
config file; `--endpoint-url`, `--access-key`, and `--secret-key` override them.
