import urllib2
import urllib
import json
import gzip

from StringIO import StringIO

class BabelnetInterface:
    """this class provides an interface with the BabelNet lexical network through HTTP GET requests"""
    def __init__(self,key):
        self.base_url = "https://babelnet.io/v5/"
        #the key is granted upon registration on BabelNet, it allows for up to 1000 requests per day
        self.key = key
        
    def _request_respond(self,url):
        """this function does the request handling with all its details"""
        request = urllib2.Request(url)
        #gzip encoding/compression of the response is recommended by the provider
        request.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(request).read()
        try:
            f=gzip.GzipFile(fileobj=StringIO(response))
            #convert json to a python dictionary
            data=json.loads(f.read())
        except IOError,ValueError:
            print response
            data={}
        return data
        
        
    def get_synsets_by_word(self,search_word,lang="EN",pos="",filterLangs=None,source=""):
        """get a Synset_list object containing all the synsets denoted by a given word. Optional arguments
        are the language of the search word, pos-tag, filter languages and source."""
        params = {'lemma' : search_word,'searchLang':lang, 'source':source, 'key'  : self.key, 
                    'pos':pos}
        if filterLangs:
            query = urllib.urlencode(params)+"&targetLang="+"&targetLang=".join(filterLangs)
        else:
            query = urllib.urlencode(params)
        rq_url = self.base_url + "getSynsetIds?" + query
    
        data = self._request_respond(rq_url)
        #~ print data
        return Synset_list(self,data)
        
    def get_synsetinfo(self,id,filterLangs=None):
        """get a Babel_synset object of all the information on a synset given its id. The filterLangs 
        argument (optional) takes a list [lang1,lang2,lang3] of up to 3 language abbrevations in which the synsetinformation should 
        be retrieved in."""
        params = {'id' : id,'key'  : self.key}
        if filterLangs:
            query = urllib.urlencode(params)+"&targetLang="+"&targetLang=".join(filterLangs)
        else:
            query = urllib.urlencode(params)
        rq_url = self.base_url + "getSynset?" + query
        #~ print rq_url
        data=self._request_respond(rq_url)
        print json.dumps(data,indent=3)
        return Babel_synset(self,id,data)
        
    def get_senses_by_word(self,search_word,lang="EN"):
        """get a json object of all the babelNet senses of a given word. This function is redundant since you can get that 
        same information better by calling 'get_senses()' on a 'get_synsetinfo' output"""
        params = {'word' : search_word, 'lang'  : lang, 'key'  : self.key}
        query = urllib.urlencode(params)
        rq_url = self.base_url + "getSenses?" + query
        data=self._request_respond(rq_url)
        return data
        
    def get_edges(self,id):
        """get a json object of all the edges connected to the synset.
        Retrieve hypernyms,hyponyms,meronyms, holonyms, antonyms, and other semantically related forms"""
        params = {'id' : id,'key'  : self.key}
        query = urllib.urlencode(params)
        rq_url = self.base_url + "getOutgoingEdges?" + urllib.urlencode(params)
        data=self._request_respond(rq_url)
        return data #json output
        
    def get_synsets_from_wiki(self,wiki_term,lang="EN",pos="",filterLangs=None,source="WIKI"):
        """get a Synset_list object of a wikipedia article. POS-tags as well as sources can be specified"""
        params = {'id' : wiki_term, 'lang'  : lang, 'pos':pos, 'source':source,'key'  : self.key}
        if filterLangs:
            query = urllib.urlencode(params)+"&targetLang="+"&targetLang=".join(filterLangs)
        else:
            query = urllib.urlencode(params)
        rq_url = self.base_url + "getSynsetIdsFromResourceID?" + query
        data=self._request_respond(rq_url)
        return Synset_list(self,data)
        
class Babel_synset:
    """this class provides basic functionality to retrieve the most important informations about a synset. An instance of this
    class is returned by the 'get_synsetinfo' function of the class 'BabelnetInterface'."""
    def __init__(self, interface, synid, synsetinfo):
        self.data=synsetinfo
        #this dict defines for each sense's source identifier the more readable lemma, so later we can assign glosses to lemmas.
        self.senses={}
        self.req_interface=interface
        self.edges={}
        self.synset_id=synid
        
        for entry in self.data["senses"]:
            key=entry["properties"]["idSense"]
            self.senses[key] = entry["properties"]["fullLemma"]
    
    def __getitem__(self,key):
        return self.data[key]           
    
    def __repr__(self):
        """the structure of the json object is represented with json.dumps with indent. This is an option to pretty-print
        a dictionary"""
        return json.dumps(self.data, indent=4)
        
    def get_main_sense(self):
        return self.data["mainSense"]
        
    def get_senses(self):
        """get all the senses reverse sorted by frequency"""            
        return [(entry["lemma"],entry["language"],entry["source"]) for entry in sorted(self.data["senses"],key=lambda x: x["frequency"], reverse=True)]
    
    def get_categories(self):
        """get all the categories of a synset"""
        return [entry["category"] for entry in self.data["categories"]]
    
    def get_glosses(self):
        """get a tuple of lemma, source-identifier and gloss"""
        glosses=[]
        for entry in self.data["glosses"]:
            try:
                sense_lemma=self.senses[entry["sourceSense"]]
            except KeyError as error:
                try:
                    sense_lemma=self.senses[entry["sourceSense"].lower()]
                except KeyError:
                    sense_lemma=entry["sourceSense"]
            glosses.append((sense_lemma,entry["sourceSense"],entry["gloss"],entry["source"]))
        return glosses
    def get_translations(self):
        """get the translation of the synset"""
        return [entry for entry in self.data["translations"]]
        
    def get_connections(self):
        """get all the Synsets that are connected to the synset"""
        if self.edges=={}:
            self.edges=self.req_interface.get_edges(self.synset_id)
        return [{"id":edge["target"],"type":edge["pointer"]["relationGroup"]} for edge in self.edges]
    
    def get_hypernyms(self):
        """get all the Synsets that are in the relation 'hypernym' with the synset"""
        hypernyms=[]
        if self.edges == {}:
            self.edges=self.req_interface.get_edges(self.synset_id)
        
        for edge in self.edges:
            if edge["pointer"]["relationGroup"]=="HYPERNYM":
                hypernyms.append(edge["target"])
        return hypernyms
        
    def get_hyponyms(self):
        """get all the Synsets that are in the relation 'hyponym' with the synset"""
        hyponyms=[]
        if self.edges == {}:
            self.edges=self.req_interface.get_edges(self.synset_id)
        
        for edge in self.edges:
            if edge["pointer"]["relationGroup"]=="HYPONYM":
                hyponyms.append(edge["target"])
        return hyponyms
        
    def get_holonyms(self):
        """get all the Synsets that are in the relation 'holonym' with the synset"""
        holonyms=[]
        if self.edges == {}:
            self.edges=self.req_interface.get_edges(self.synset_id)
        
        for edge in self.edges:
            if edge["pointer"]["relationGroup"]=="HOLONYM":
                holonyms.append(edge["target"])
        return holonyms
        
    def get_meronyms(self):
        """get all the Synsets that are in the relation 'meronym' with the synset"""
        meronyms=[]
        if self.edges == {}:
            self.edges=self.req_interface.get_edges(self.synset_id)
        
        for edge in self.edges:
            if edge["pointer"]["relationGroup"]=="MERONYM":
                meronyms.append(edge["target"])
        return meronyms
        
class Synset_list:
    """this class handles the synset list from the 'get_synsets_by_word' method. If your term has only one synset
    assigned to, this class won't be able to help you a lot."""
    def __init__(self,interface,my_list):
        self.req_interface=interface
        self.synlist=my_list
        self.synsets={}
        self.edges={}
        
    def __len__(self):
        return len(self.synlist)
        
    def __contains__(self,item):
        return item in self.synlist
    def __add__(self,other_sequence):
        return Synset_list(self.synlist + other_sequence)
        
    def __getitem__(self,key):
        if isinstance(key,slice):
            return Synset_list(self.synlist[key.start:key.stop:key.step])
        else:
            return self.synlist[key]
            
    def __setitem__(self,key,item):
        self.synlist[key]=item
        
    def __repr__(self):
        return json.dumps(self.synlist, indent=4)
    
    def get_IDs(self):
        """returns a list of all the babelsynset identifiers in the synsetlist"""
        return [synset["id"] for synset in self.synlist]
        
    def list_main_senses(self,num_of_senses=None):
        """assigns the synset identifier to the most prominent sense of the synset and lists them in
        tuple of id, synset type and sense. Be aware that the function performs n database requests
        with n as the number of synsets"""
        self.main_senses=[]
        
        for synset in self.synlist[:num_of_senses]:
            try:
                syn_object=self.synsets[synset["id"]]
                self.main_senses.append((syn_object["mainSense"],syn_object["lang"]))
            except KeyError:
                syn_object=self.req_interface.get_synsetinfo(synset["id"])
                self.synsets[synset["id"]]=syn_object
                self.main_senses.append((synset["id"],syn_object["synsetType"],syn_object["mainSense"]))
                
        return self.main_senses
            
    def sort_by_relevance(self):
        """no return value. sorts the synsets in place according to the number of edges connected to the synset.
        Be aware that the function performs n database requests with n as the number of synsets."""
        for synset in self.synlist:
            try:
                edge_list=self.edges[synset["id"]]
                synset["semRels"] = len(edge_list)
            except KeyError:
                edge_list=self.req_interface.get_edges(synset["id"])
                self.edges[synset["id"]]=edge_list
                synset["semRels"] = len(edge_list)
        
        self.synlist = sorted(self.synlist, key=lambda x: x["semRels"], reverse=True)
        
        

if __name__=="__main__":
    #example usage
    
    
    #specify your own babelNet key from: http://babelnet.org/register  or use my key
    #this class sets up a HTTP interface with the database
    
    babelnet = BabelnetInterface("<key>")
    
    #here you can search synsets by word. It is possible to define a pos-tag and you can give an array
    #of filter languages get synsets in other languages too.
    my_synsets = babelnet.get_synsets_by_word("Israeli",pos="ADJ")
    print my_synsets.list_main_senses()
    #iterate through the synset list and retrieve the synsetinfo for each synset
    for entity in my_synsets.get_IDs():
        synset=babelnet.get_synsetinfo(entity,filterLangs=["DE","FR"])
        #~ print synset
        print synset.get_connections()
        #print json.dumps(edges, indent=4)
    
        
        
    
    
            
    
