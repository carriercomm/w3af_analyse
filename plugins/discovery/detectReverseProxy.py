'''
detectReverseProxy.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import core.controllers.outputManager as om
# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.w3afException import w3afException
import core.data.kb.knowledgeBase as kb
import core.data.kb.info as info
from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin
import re
from core.controllers.w3afException import w3afRunOnce

class detectReverseProxy(baseDiscoveryPlugin):
    '''
    Find out if the remote web server has a reverse proxy.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''
    
    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        self._run = True
        
        # Some internal variables
        self._proxyHeaderList = ['Via','Reverse-Via','X-Forwarded-For','Proxy-Connection']
        
    def discover(self, fuzzableRequest ):
        '''
        @parameter fuzzableRequest: A fuzzableRequest instance that contains (among other things) the URL to test.
        '''
        if not self._run:
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
        else:
            # I will only run this one time. All calls to detectReverseProxy return the same url's
            self._run = False
            
            # detect using GET
            if not kb.kb.getData( 'detectTransparentProxy', 'detectTransparentProxy'):            
                response = self._urlOpener.GET( fuzzableRequest.getURL(), useCache=True )
                if self._hasProxyHeaders( response ):
                    self._reportFinding( response )
           
            # detect using TRACE
            # only if I wasn't able to do it with GET
            if not kb.kb.getData( 'detectReverseProxy', 'detectReverseProxy' ):
                response = self._urlOpener.TRACE( fuzzableRequest.getURL(), useCache=True )
                if self._hasProxyContent( response ):
                    self._reportFinding( response )
           
            # detect using TRACK
            # This is a rather special case that works with ISA server; example follows:
            # Request:
            # TRACK http://www.xyz.com.bo/ HTTP/1.1
            # ...
            # Response headers:
            # HTTP/1.1 200 OK
            # content-length: 99
            # ...
            # Response body:
            # TRACK / HTTP/1.1
            # Reverse-Via: MUTUN ------> find this!
            # ....
            if not kb.kb.getData( 'detectReverseProxy', 'detectReverseProxy' ):
                response = self._urlOpener.TRACK( fuzzableRequest.getURL(), useCache=True )
                if self._hasProxyContent( response ):
                    self._reportFinding( response )
                
            # Report failure to detect reverse proxy
            if not kb.kb.getData( 'detectReverseProxy', 'detectReverseProxy' ):
                om.out.information( 'The remote web server doesn\'t seem to have a reverse proxy.' )

        return []
        
    def _reportFinding( self, response ):
        i = info.info()
        i.setName('Reverse proxy')
        i.setId( response.getId() )
        i.setURL( response.getURL() )
        i.setDesc( 'The remote web server seems to have a reverse proxy installed.' )
        i.setName('Found reverse proxy')
        kb.kb.append( self, 'detectReverseProxy', i )
        om.out.information( i.getDesc() )
    
    def _hasProxyHeaders( self, response ):
        '''
        Performs the analysis
        @return: True if the remote web server has a reverse proxy
        '''
        for proxyHeader in self._proxyHeaderList:
            for responseHeader in response.getHeaders():
                if proxyHeader.upper() == responseHeader.upper():
                    return True
                else:
                    return False
                    
    def _hasProxyContent( self, response ):
        '''
        Performs the analysis of the response of the TRACE and TRACK command.
        
        @parameter response: The HTTP response object to analyze
        @return: True if the remote web server has a reverse proxy
        '''
        responseBody = response.getBody().upper()
        #remove duplicated spaces from body
        whitespace = re.compile('\s+')
        responseBody = re.sub(whitespace, ' ', responseBody)
        
        for proxyHeader in self._proxyHeaderList:
            # Create possible header matches
            possibleMatches = [proxyHeader.upper() + ':',  proxyHeader.upper() + ' :']
            for possibleMatch in possibleMatches:
                if possibleMatch in responseBody:
                    return True
                else:
                    return False

    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol

    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass
        
    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return ['discovery.detectTransparentProxy']

    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin tries to determine if the remote end has a reverse proxy installed.
        
        The procedure used to detect reverse proxies is to send a request to the remote server and analyze the response headers,
        if a Via header is found, chances are that the remote site has a reverse proxy.
        '''
