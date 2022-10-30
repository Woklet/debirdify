import re
import tweepy

# Matches anything of the form @foo@bar.bla or foo@bar.social or foo@social.bar or foo@barmastodonbla
# We do not match everything of the form foo@bar or foo@bar.bla to avoid false positives like email addresses
_id_pattern1 = re.compile(r'(@[^\s(),:;#]+@[^\s():;#]+\.[^\s(),:;#]+|[^\s(),:;#]+@[^\s(),:;#]+\.social|[^\s(),:;#]+@social\.[^\s(),:;#]+|[^\s(),:;#]+@[^\s(),:;#]*mastodon[^\s(),:;#]+)', re.IGNORECASE)
_id_pattern2 = re.compile(r'\b(http://|https://)([^\s(),:;#/])+/@([^\s(),:;#/]+)(/)?\b', re.IGNORECASE)

# Matches some key words that might occur in bios
_keyword_pattern = re.compile(r'.*(mastodon|toot|tröt).*', re.IGNORECASE)

class MastodonID:
    def __init__(self, user_part, host_part):
        self.user_part = user_part
        self.host_part = host_part

    def __str__(self):
        return '{}@{}'.format(self.user_part, self.host_part)
        
    def url(self):
        return 'https://{}/@{}'.format(self.host_part, self.user_part)
        
def parse_mastodon_id(s):
    if s[:1] == '@':
        s = s[1:]
    tmp = s.split('@')
    if len(tmp) != 2:
        return None
    return MastodonID(tmp[0], tmp[1])       

class UserResult:
    def __init__(self, uid, name, screenname, bio, mastodon_ids, extras):
        self.uid = uid
        self.name = name
        self.screenname = screenname
        self.bio = bio
        self.mastodon_ids = mastodon_ids
        self.extras = extras

# client: a tweepy.Client object
# requested_user: a tweepy.User object
# returns:
#   a tuple consisting of two lists UserResult objects.
#   the first component contains a list of users that seem to have a Mastodon ID in their name or bio
#   the second component contains a list of users that have some keyword in their bio that looks Mastodon-related
def extract_mastodon_ids(client, requested_user):
    if requested_user is None: return None
    resp = client.get_users_following(requested_user.id, max_results=1000, user_auth=True, user_fields=['name', 'username', 'description'])
    users = resp.data
    results1 = list()
    results2 = list()
    
    for u in users:
       uid = u.id
       name = u.name
       screenname = u.username
       bio = u.description
       mastodon_ids = set()
       mastodon_ids1 = [mid for s in _id_pattern1.findall(screenname) + _id_pattern1.findall(bio)
                            if (mid := parse_mastodon_id(s)) is not None]
       mastodon_ids2 = [MastodonID(u, h) for _, h, u, _ in _id_pattern2.findall(screenname) + _id_pattern2.findall(bio)]
       mastodon_ids = list(set(mastodon_ids1).union(set(mastodon_ids2)))
       extras = None
       
       if not mastodon_ids:
         extras = list()
         for d in u.description.splitlines():
             if _keyword_pattern.match(d): extras.append(d)
         if not extras: extras = None
         
       if mastodon_ids:
           results1.append(UserResult(uid, name, screenname, bio, mastodon_ids, extras))
       elif extras is not None:
           results2.append(UserResult(uid, name, screenname, bio, mastodon_ids, extras))

    return (results1, results2)

