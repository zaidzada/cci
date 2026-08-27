"""Command-line interface for cottoncandy.

Exposes the ``BasicInterface``/``FileSystemInterface`` functionality
(``cottoncandy.get_interface()``) as a ``cottoncandy`` command line tool.
"""
import argparse
import os
import sys

import cottoncandy as cc
from cottoncandy.utils import bytes2human

# S3-only operations: buckets are not a concept on the local/gdrive backends
_BUCKET_LEVEL_BACKENDS = ('s3',)


def _get_interface(args, bucket_name=None, verbose=False):
    kwargs = { 'backend': args.backend, 'verbose': verbose }
    if bucket_name is not None:
        kwargs['bucket_name'] = bucket_name
    elif args.bucket is not None:
        kwargs['bucket_name'] = args.bucket
    # else: leave unset so cc.get_interface() falls back to the configured default_bucket

    if args.endpoint_url:
        kwargs['endpoint_url'] = args.endpoint_url
    if args.access_key:
        kwargs['ACCESS_KEY'] = args.access_key
    if args.secret_key:
        kwargs['SECRET_KEY'] = args.secret_key

    cci = cc.get_interface(**kwargs)
    return cci


def _require_bucket(cci):
    if not cci.bucket_name:
        sys.exit('No bucket specified. Use -b/--bucket, or set "default_bucket" '
                 'in your cottoncandy config file.')


def _require_s3_backend(args, command):
    if args.backend not in _BUCKET_LEVEL_BACKENDS:
        sys.exit('"%s" is only supported for the s3 backend (got: %s)' % (command, args.backend))


def cmd_list(args):
    _require_s3_backend(args, 'list')
    cci = _get_interface(args, bucket_name='')
    cci.show_buckets()


def cmd_ls(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    for name in sorted(cci.ls(args.pattern)):
        print(name)


def cmd_lsdir(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    for name in cci.lsdir(args.path):
        print(name)


def cmd_glob(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    for name in cci.glob(args.pattern):
        print(name)


def cmd_mb(args):
    _require_s3_backend(args, 'mb')
    cci = _get_interface(args, bucket_name='')
    cci.create_bucket(args.bucket_name)
    print('Created bucket "%s"' % args.bucket_name)


def cmd_rb(args):
    _require_s3_backend(args, 'rb')
    cci = _get_interface(args, bucket_name='')
    cci.rm_bucket(args.bucket_name)


def cmd_rm(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    cci.rm(args.object_name, recursive=args.recursive)


def cmd_cp(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    cci.cp(args.source, args.dest,
          dest_bucket=args.dest_bucket, overwrite=args.overwrite)


def cmd_mv(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    cci.mv(args.source, args.dest,
          dest_bucket=args.dest_bucket, overwrite=args.overwrite)


def cmd_upload(args):
    cci = _get_interface(args)
    _require_bucket(cci)

    local_path = args.local_path
    if not os.path.exists(local_path):
        sys.exit('No such file or directory: "%s"' % local_path)

    if os.path.isdir(local_path):
        if not args.recursive:
            sys.exit('"%s" is a directory. Use -r/--recursive to upload directories.' % local_path)
        cci.upload_from_directory(local_path, args.object_name, recursive=True)
    else:
        object_name = args.object_name or os.path.basename(local_path)
        cci.upload_from_file(local_path, object_name)
        print('Uploaded "%s" to "%s"' % (local_path, object_name))


def cmd_download(args):
    cci = _get_interface(args)
    _require_bucket(cci)

    object_name = args.object_name
    if args.recursive:
        local_path = args.local_path or os.path.basename(object_name.rstrip('/'))
        cci.download_directory(object_name, local_path)
    else:
        cci.exists_object(object_name, raise_err=True)
        local_path = args.local_path or os.path.basename(object_name)
        cci.download_to_file(object_name, local_path)
        print('Downloaded "%s" to "%s"' % (object_name, local_path))


def cmd_du(args):
    cci = _get_interface(args)
    _require_bucket(cci)
    total_bytes = cci.get_size()
    print('%s (%i bytes)' % (bytes2human(total_bytes), total_bytes))


def build_parser():
    parser = argparse.ArgumentParser(
        prog='cottoncandy',
        description='Command line interface for cottoncandy.')
    parser.add_argument('-b', '--bucket', default=None,
                        help='Bucket to operate on. Defaults to "default_bucket" in your '
                             'cottoncandy config file.')
    parser.add_argument('--backend', default='s3', choices=['s3', 'gdrive', 'local'],
                        help='Storage backend to use (default: s3)')
    parser.add_argument('--endpoint-url', default=None,
                        help='S3 endpoint URL (overrides config)')
    parser.add_argument('--access-key', default=None,
                        help='Access key (overrides config/environment)')
    parser.add_argument('--secret-key', default=None,
                        help='Secret key (overrides config/environment)')

    subparsers = parser.add_subparsers(dest='command', required=True)

    sub = subparsers.add_parser('list', help='List available buckets')
    sub.set_defaults(func=cmd_list)

    sub = subparsers.add_parser('ls', help='List objects matching a glob-style pattern')
    sub.add_argument('pattern', nargs='?', default='*')
    sub.set_defaults(func=cmd_ls)

    sub = subparsers.add_parser('lsdir', help='List the immediate contents of a "directory"')
    sub.add_argument('path', nargs='?', default='/')
    sub.set_defaults(func=cmd_lsdir)

    sub = subparsers.add_parser('glob', help='Print objects matching a glob pattern')
    sub.add_argument('pattern')
    sub.set_defaults(func=cmd_glob)

    sub = subparsers.add_parser('mb', help='Create a new bucket')
    sub.add_argument('bucket_name')
    sub.set_defaults(func=cmd_mb)

    sub = subparsers.add_parser('rb', help='Remove an empty bucket')
    sub.add_argument('bucket_name')
    sub.set_defaults(func=cmd_rb)

    sub = subparsers.add_parser('rm', help='Delete an object, or a subtree')
    sub.add_argument('object_name')
    sub.add_argument('-r', '--recursive', action='store_true',
                     help='Remove a subtree recursively')
    sub.set_defaults(func=cmd_rm)

    sub = subparsers.add_parser('cp', help='Copy an object')
    sub.add_argument('source')
    sub.add_argument('dest')
    sub.add_argument('--dest-bucket', default=None,
                     help='Destination bucket, if different from the source bucket')
    sub.add_argument('--overwrite', action='store_true',
                     help='Overwrite the destination if it already exists')
    sub.set_defaults(func=cmd_cp)

    sub = subparsers.add_parser('mv', help='Move (rename) an object')
    sub.add_argument('source')
    sub.add_argument('dest')
    sub.add_argument('--dest-bucket', default=None,
                     help='Destination bucket, if different from the source bucket')
    sub.add_argument('--overwrite', action='store_true',
                     help='Overwrite the destination if it already exists')
    sub.set_defaults(func=cmd_mv)

    sub = subparsers.add_parser('upload', help='Upload a local file or directory')
    sub.add_argument('local_path')
    sub.add_argument('object_name', nargs='?', default=None,
                     help='Name to use in the cloud. Defaults to the local file/directory name.')
    sub.add_argument('-r', '--recursive', action='store_true',
                     help='Required when uploading a directory')
    sub.set_defaults(func=cmd_upload)

    sub = subparsers.add_parser('download', help='Download an object or a subtree to disk')
    sub.add_argument('object_name')
    sub.add_argument('local_path', nargs='?', default=None,
                     help='Path to download to. Defaults to the object name.')
    sub.add_argument('-r', '--recursive', action='store_true',
                     help='Download a whole subtree')
    sub.set_defaults(func=cmd_download)

    sub = subparsers.add_parser('du', help='Show the total size of the current bucket')
    sub.set_defaults(func=cmd_du)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except SystemExit:
        raise
    except Exception as e:
        message = str(e) or '%s raised with no message' % type(e).__name__
        sys.exit('Error: %s' % message)


if __name__ == '__main__':
    main()
