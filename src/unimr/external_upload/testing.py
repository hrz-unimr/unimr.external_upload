from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting

from plone.testing import z2

from zope.configuration import xmlconfig


class Unimrexternal_UploadLayer(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import unimr.external_upload
        xmlconfig.file(
            'configure.zcml',
            unimr.external_upload,
            context=configurationContext
        )

        # Install products that use an old-style initialize() function
        #z2.installProduct(app, 'Products.PloneFormGen')

#    def tearDownZope(self, app):
#        # Uninstall products installed above
#        z2.uninstallProduct(app, 'Products.PloneFormGen')


UNIMR_EXTERNAL_UPLOAD_FIXTURE = Unimrexternal_UploadLayer()
UNIMR_EXTERNAL_UPLOAD_INTEGRATION_TESTING = IntegrationTesting(
    bases=(UNIMR_EXTERNAL_UPLOAD_FIXTURE,),
    name="Unimrexternal_UploadLayer:Integration"
)
