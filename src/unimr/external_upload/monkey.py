import urlparse
from os.path import isfile
from os import unlink, fdopen

from cgi import valid_boundary
from cgi import rfc822
from cgi import MiniFieldStorage
from cgi import parse_header

from tempfile import mkstemp, _TemporaryFileWrapper as TFW

from ZPublisher import HTTPRequest

try:
    from plone.app.blob.monkey import NamedFieldStorage as FS
except:
    from cgi import FieldStorage as FS


from logging import getLogger

logger = getLogger('unimr.external_upload')

# token from plone.app.blob.monkey
class TemporaryFileWrapper(TFW):
    """ variant of tempfile._TemporaryFileWrapper that doesn't rely on the
        automatic windows behaviour of deleting closed files, which even
        happens, when the file has been moved -- e.g. to the blob storage,
        and doesn't complain about such a move either """

    unlink = staticmethod(unlink)
    isfile = staticmethod(isfile)

    def close(self):
        if not self.close_called:
            self.close_called = True
            self.file.close()

    def __del__(self):
        self.close()
        if self.isfile(self.name):
            self.unlink(self.name)

            
class NginxFieldStorage(MiniFieldStorage):
    """Like FieldStorage, for use when nginx bypasses a file upload."""

    # Dummy attributes
    filename = None
    list = None
    type = None
    file = None
    type_options = {}
    disposition = None
    disposition_options = {}
    headers = {}

    def __init__(self, name, filename, path, content_type):
        """Constructor from field name, filename, path of binary blob and content_type."""

        self.name = name
        self.filename = filename
        self.type = content_type
        self.disposition = "form-data"
        self.disposition_options = {'name': self.name, 'filename': self.filename}

        self.headers['content-disposition'] = "form-data; name=\"%s\"; filename=\"%s\"" % (self.name, self.filename)
        self.headers['content-type'] = self.type

        assert isfile(path), 'NginxFieldStorage: invalid upload file: %s' % path

        self.file = TemporaryFileWrapper(open(path, 'rb'), path)

        self.__path = path

    def __repr__(self):
        """Return printable representation."""
        return "NginxFieldStorage(%r, %r, %r, %r)" % (self.name, self.filename, self.__path, self.type)

class FieldStorageWrapper(FS):
    """Wrapper for FieldStorage"""

    def read_multi(self, environ, keep_blank_values, strict_parsing):
        """Internal: read a part that is itself multipart."""

        ib = self.innerboundary
        if not valid_boundary(ib):
            raise ValueError, 'Invalid boundary in multipart form: %r' % (ib,)
        self.list = []
        if self.qs_on_post:
            for key, value in urlparse.parse_qsl(self.qs_on_post,
                                self.keep_blank_values, self.strict_parsing):
                self.list.append(MiniFieldStorage(key, value))
            # never used!? self.FieldStorageClass?
            FieldStorageClass = None

        klass = self.FieldStorageClass or self.__class__
        part = klass(self.fp, {}, ib,
                     environ, keep_blank_values, strict_parsing)
        # Throw first part away
        while not part.done:
            headers = rfc822.Message(self.fp)
            part = klass(self.fp, headers, ib,
                         environ, keep_blank_values, strict_parsing)
            self.list.append(part)
        self.skip_lines()

        for fieldname in self.keys():
            if fieldname.endswith('.ngx_upload'):
                  
                fn_patterns = { 'name': '%s.ngx_upload', 'filename': '%s.filename', 'path': '%s.path', 'content_type': '%s.content_type' }

                fn_dict = {}
                upload_fn =  self.getvalue(fieldname)
                for k,p in fn_patterns.items():
                    fn = p % upload_fn
                    fn_dict[k] = self.getvalue(fn)

                    # cleanup nginx stuff
                    del self[fn]
                    
                logger.debug('Nginx File Upload (%(name)s, %(filename)s, %(path)s, %(content_type)s)' % fn_dict)
                self.list.append(NginxFieldStorage(**fn_dict))     

                
    def make_file(self, binary=None):
        handle, name = mkstemp()
        return TemporaryFileWrapper(fdopen(handle, 'w+b'), name)

    def __delitem__(self,key):

        if self.has_key(key):
            self.list.remove(self[key])
        else:
            raise KeyError
        
        
def patch():
    logger.info('patching HTTPRequest.(Zope)FieldStorage')
    HTTPRequest.FieldStorage = FieldStorageWrapper
    HTTPRequest.ZopeFieldStorage = FieldStorageWrapper



