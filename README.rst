Introduction
============

Even though Zope with ZODB blobs is capable of handling big file uploads, its performance is weak in comparison to Nginx upload module.

Using the latter has many advantages, e.g.:

* The upload module is native C code. It is much faster then the python based implementation.

* Long running uploads don't block Zope's thread pool for other incoming requests.


Prerequisites
=============

Nginx delivers the uploaded files to zope by means of a shared (distributed) file system. Therefore, nginx and zope must run under the same uid (e.g. www-data) in order to avoid ACL problems during the file transfer process.


Recommendation
==============

In order to avoid unnecessary file system IO Zope's TMPDIR should be on the same volume as Nginx's upload_store (s.a. `HOWTO-Blobs-NFS.txt <https://github.com/zopefoundation/ZODB/blob/master/doc/HOWTO-Blobs-NFS.txt>`_).


Enabling unimr.external_upload
==============================

These instructions are for Github version. 

Then include it in the buildout.cfg::


       [buildout]
       ...
       parts = instance
       find-links =
          http://github.com/hrz-unimr/unimr.external_upload/tarball/master#egg=unimr.external_upload
       ...
       
       [instance]
       ...
       eggs = unimr.external_upload
       effective-user = www-data
       ...


Installation on Nginx
=====================

Here's a nginx site configuration

mysite::


     # This specifies which IP and port Plone is running on.
     # The default is 127.0.0.1:8080
     upstream plone {
         server 127.0.0.1:8080;
     }

     # virtual server
     server {

         listen 80;
         client_max_body_size 1000m;

         server_name www.mysite.org;

         access_log /var/log/nginx/www.mysite.org.access.log;
         error_log /var/log/nginx/www.mysite.org.error.log;

         # Note that domain name spelling in VirtualHostBase URL matters
         # -> this is what Plone sees as the "real" HTTP request URL.
         # "Plone" in the URL is your site id (case sensitive)
         location / {
               proxy_pass http://plone/VirtualHostBase/http/localhost:8081/Plone/VirtualHostRoot/;
         }

         # Upload module section
         # Upload form should be submitted to this location. In Plone is the correct 
         # location at any context "atct_edit" for ATContentTypes.
         location ~ .*/atct_edit$ {
             # Pass altered request body to this location
             upload_pass   @upload;

             # Store files to this directory
             # The directory is hashed, subdirectories 0 1 2 3 4 5 6 7 8 9 should exist
             upload_store /<path_to_tmpdir>/ngx_upload 1;

             # Allow uploaded files to be read/write only by user and group
             # Plone has to be run under same uid as nginx
             upload_store_access user:rw group:rw;

             # Nginx marker for upload field
             upload_set_form_field $upload_field_name.ngx_upload "$upload_field_name";

             # Set specified fields in request body
             upload_set_form_field $upload_field_name.filename "$upload_file_name";
             upload_set_form_field $upload_field_name.content_type "$upload_content_type";
             upload_set_form_field $upload_field_name.path "$upload_tmp_path";

             # Notify backend about checksum and size of a file (currently not used in Plone)
             upload_aggregate_form_field "$upload_field_name.md5" "$upload_file_md5";
             upload_aggregate_form_field "$upload_field_name.size" "$upload_file_size";

             # pass all fields except the file upload field itself
             upload_pass_form_field "^.*$";

             upload_cleanup 400-599;
         }

         # Internal location for upload handling
         location @upload {
             proxy_pass http://plone/VirtualHostBase/http/localhost:8081/Plone/VirtualHostRoot/$request_uri;
         }
     }
