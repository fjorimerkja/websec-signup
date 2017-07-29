import hashlib
import json

from django.http import HttpResponse
from django.shortcuts import render, render_to_response
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

from models import Word, Student, CrawlerURL
import pymysql
import sqlparse


def add_student(request, first_name, last_name, email, access_token):
    # TODO: this needs to be accessible only for an admin, so for now it is not linked to
    conn = pymysql.connect("127.0.0.1", "websec_ui", "websec", "websec")
    conn.autocommit = True
    cur = conn.cursor()

    # stored procedures allow for nice fine-grained access rights. All we really need to do to signup is to call
    # the function here :-)
    cur.execute("""
    CALL signup("Fjori", "M", "fjorimerkja@gmail.com", "fm")
    """, (first_name, last_name, email, access_token))


def generate_access_token(request):
    if request.method != 'GET':
        return HttpResponse("no!")
    first_name = request.GET.get('first_name', None)
    last_name = request.GET.get('last_name', None)

    if request.META["REMOTE_ADDR"] not in ('134.96.225.205', '127.0.0.1'):
        return HttpResponse("YouAreNotAuthorized")
    else:
        secret = open("secret", "rb").read()
        return HttpResponse(hashlib.sha1(first_name + last_name + secret).hexdigest())


def search(request):
    if request.method != 'GET':
        return HttpResponse("no!")

    searchword = request.GET.get("searchword", "dummy")
    fuzzy_matching = request.GET.get("fuzzy_matching", None)

    if fuzzy_matching == 'y':
        # I am too lazy to understand how fuzzy matching works with objects, so let's just go with a regular SQL query
        conn = pymysql.connect("127.0.0.1", "websec_ui", "websec", "websec")
        conn.autocommit = True
        cur = conn.cursor()

        query = "SELECT word, frequency FROM signup_word WHERE word LIKE '%{}%';".format(searchword)
        words = list()

        # I found this code somewhere. Don't know why I would have multiple statements in my query, but utility
        # is much more important than trying to understand security implications of this.
        for statement in sqlparse.split(query):
            try:
                cur.execute(statement)
            except Exception, e:
                # in case something goes wrong, we need to be able to debug properly. So, let's output the error message
                return render_to_response("error.html", {"query": statement, "error": str(e)})

            for row in cur.fetchall():
                word = {"word": row[0], "frequency": row[1]}
                words.append(word)

    elif fuzzy_matching == 'n':
        words = Word.objects.filter(word=searchword)
        # We trust the user to not put anything bad in the searchword.
        searchword = mark_safe(searchword)

    else:
        words = []
        searchword = "Search for a word"

    response = render_to_response("search.html",
                                  {"searchword": searchword, "words": words[:100],
                                   "fuzzy": fuzzy_matching or "n"})
    # Who needs protection from XSS?
    response["X-XSS-Protection"] = "0"

    return response


def check_status(request):
    if request.method != 'GET':
        return HttpResponse("no!")

    access_token = request.GET.get("access_token")

    if not access_token:
        return render_to_response("check_student.html", {"msgclass": "info", "msg": "Please search for an access token"})

    if access_token:
        try:
            student = Student.objects.get(access_token=access_token)
        except Student.DoesNotExist:
            return render_to_response("check_student.html",
                                      {"msgclass": "danger", "msg": "No such token."})

        secret = open("secret", "rb").read()
        valid_token = hashlib.sha1(student.first_name + student.last_name + secret).hexdigest()

        if valid_token == access_token:
            return render_to_response("check_student.html",
                                      {"msgclass": "success", "msg": "Student registered with that token."})
        else:
            return render_to_response("check_student.html",
                                      {"msgclass": "warning", "msg": "Token exists, but does not match student."})


@csrf_exempt
def submit_url(request):
    if request.method == 'POST':
        url = request.POST.get("url")
        if not url.startswith("https://websec.cispa.saarland/"):
            return render_to_response("submiturl.html", {"message": "Don't use URLs outside of the lecture site"})
        if CrawlerURL.objects.filter(url=url):
            return render_to_response("submiturl.html", {"message": "This URL was already added. Please wait for it to "
                                                                    "be visited or try submitting a different one"})
        else:
            CrawlerURL(url=url).save()
            return render_to_response("submiturl.html", {"message": "URL added. Please wait for the crawler to visit it"})

    return render_to_response("submiturl.html")


def get_urls(request):
    if request.META["REMOTE_ADDR"] not in ('134.96.225.205', '127.0.0.1'):
        return HttpResponse("YouAreNotAuthorized")

    urls = CrawlerURL.objects.filter(visited=False)
    if len(urls) > 0:
        url_to_visit = urls[0]
        url_to_visit.visited = True
        url_to_visit.save()
        return HttpResponse(json.dumps([url_to_visit.url]), content_type="application/json")

    return HttpResponse(json.dumps([]), content_type="application/json")
