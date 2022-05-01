# SPDX-License-Identifier: 0BSD
# Copyright (c) 2022 by technojo4@gmail.com

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLine, LTChar, LAParams

# constants: font size
# thresholds, not exact numbers (comparison to use at start of description comment)
SIZE_NORMAL = 11 # > normal text
SIZE_SECTION = 13.0 # > section names
SIZE_CHAPTER = 23.0 # > chapter names
SIZE_CHAPTERNUM = 19.0 # > chapter numbers
SIZE_BIGLETTER = 31.0 # > first letters of chapters
SIZE_REFNUMBER = 7.0 # < footnote numbers
SIZE_SMALLTEXT = 10.0 # < blockquote, footnote content

# other constants
Y_MAX = 640
X_MIN = 24
X_MIN2 = 40
X_MIN3 = 60

x0chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.“”’()[]"

# text that appears at the start of blockquotes with inverted indentation
# hardcoded this way because, unlike bullet lists and other madness,
# there is legitimately nothing one can use to tell whether a blockquote will have inverted indentation
INVERTED_START = [
    "Am I violating any laws or anything like that?", # p. 136
    "enable communities to use mutual credit currencies", # 196
    "Why are we trying to recreate a college lecture?", # 224
    "The global financial and economic system is now a network", # 336
    "antiglobalization  movement  was  the  first  step  on  the  road", # 378
]

INVERTED_END = [
    "Shortly  thereafter,  Wheelan  got  in  his  car  and  drove  away", # p.136
    "Our software, based on Drupal, is the only community currency", # 196
    "explored significant parts of courses, which may be all they wanted or needed", # 225
    "over the long run, I believe this phrase is going to look as silly", # 337
    "The beauty of this new formula, and what makes this novel tactic exciting", # 378
]

# working variables
paragraphs = ["""#title The Desktop Regulatory State
#subtitle The Countervailing Power of Individuals and Networks
#author Kevin A. Carson
#SORTauthors Kevin Carson
#LISTtitle Desktop Regulatory State
#SORTtopics c4ss, technology, decentralization
#date March 2016
#source Retrieved on 8<sup>th</sup> April 2022 from [[https://kevinacarson.org/publication/drs/][kevinacarson.org]]
#lang en\n"""]

ignore = 0
footnotes = []
footnote_total = 0

chnum = None
italic = False
wasbq = False
fwasbq = False
inverted = False
bulletlist = False
biblio = False
bibliolink = False


# remove title pages + toc (start) & about author + index (end)
pages = list(range(8, 453))

page = pages[0]
# line_margin=0.0 to force it to not do automatic line analysis, it's actually easier to do it ourselves
for page_layout in extract_pages("pdf/drs_cropped.pdf", page_numbers=pages, laparams=LAParams(line_margin=0.0, char_margin=4.0)):
    page += 1
    print("Page", page)

    lines = []
    for e in page_layout:
        if e.y1 > Y_MAX: continue

        if not isinstance(e, LTTextContainer): continue
        if isinstance(e, LTTextLine): continue

        lines.extend(list(e))

    lines.sort(reverse=True, key=lambda l: l.y1)

    first = True
    for line in lines:
        chars = list(line)
        linetext = line.get_text().strip()

        # font size of first characters
        fontsize0 = chars[0].size

        # end last footnote if first line of page
        if first and paragraphs[-1][0] == "[" and paragraphs[-1][1].isdigit(): #]
            footnotes.append(paragraphs[-1])
            del paragraphs[-1]
            footnote_total = len(footnotes)

        # chapter number
        if SIZE_CHAPTER > fontsize0 > SIZE_CHAPTERNUM:
            chnum = linetext
            continue

        # chapter name
        if SIZE_BIGLETTER > fontsize0 > SIZE_CHAPTER:
            if "Bibliography" in linetext:
                biblio = True

            if chnum is None:
                paragraphs.append(f"** {linetext}")
            else:
                paragraphs.append(f"** {chnum}. {linetext}")
                chnum = None
            continue

        # section name
        if SIZE_CHAPTERNUM > fontsize0 > SIZE_SECTION:
            paragraphs.append(f"*** {linetext}")
            continue

        # first letter of chapter is 2 lines high
        if len(linetext) == 1 and fontsize0 > SIZE_BIGLETTER:
            paragraphs.append(linetext)
            ignore = 2
            continue

        # bibliography, completely different rules
        if biblio:
            new_para = line.x0 < X_MIN

            linetext = []
            for char in chars:
                if isinstance(char, LTChar):
                    i0 = italic
                    italic = "Italic" in char.fontname
                    if italic and not i0:
                        linetext.append("<em>")
                    elif i0 and not italic:
                        linetext.append("</em>")

                    c = char.get_text()
                    linetext.append(c)
                    if c == "<": bibliolink = True
                    elif c == ">": bibliolink = False

            linetext = "".join(linetext).strip()
            if new_para:
                paragraphs.append(linetext)
            else:
                p = paragraphs[-1]
                if p[-1] == "-" and not bibliolink:
                    paragraphs[-1] = p[:-1] + linetext
                elif bibliolink:
                    paragraphs[-1] += linetext.strip()
                else:
                    paragraphs[-1] += " " + linetext

            continue

        # get x0, ignoring special characters
        x0 = [c.x0 for c in chars if isinstance(c, LTChar) and c.get_text() in x0chars]
        x0 = min(x0) if len(x0) > 0 else line.x1
        if linetext == "at": x0 = 0 # hack for p. 352

        # block quotes and footnote content uses this font size, but
        # footnote content starts with the footnote number which is much smaller,
        # unless they are continued footnote content, which will have x0 < X_MIN.
        blockquote = (SIZE_REFNUMBER < fontsize0 < SIZE_SMALLTEXT) and x0 > X_MIN
        if first and fwasbq:
            wasbq = True
            fwasbq = False
            p = paragraphs[-1]
            if p.endswith("</quote>"):
                paragraphs[-1] = p[:-8]

        if blockquote:
            if any([(l in linetext) for l in INVERTED_START]):
                inverted = True
            elif any([(l in linetext) for l in INVERTED_END]):
                inverted = False

        new_para = (((inverted and blockquote) ^ (X_MIN3 > x0 > X_MIN2))
                or (not blockquote and x0 > X_MIN)
                or (blockquote ^ wasbq))

        if bulletlist:
            if not new_para:
                bulletlist = False
            new_para = "•" in linetext
        elif "•" in linetext:
            bulletlist = True

        linetext = []

        refn = False
        for char in chars:
            if isinstance(char, LTChar):
                if char.size < SIZE_REFNUMBER:
                    if not refn:
                        linetext.append("[") #]
                        refn = ""
                    refn += char.get_text()
                    continue
                if refn:
                    linetext.append(str(int(refn) + footnote_total))
                    linetext.append("]")
                    refn = False
                    if linetext[0] == "[":
                        linetext.append(" ")
                        if wasbq: fwasbq = True
                        refn = None # special value so we can tell later

                i0 = italic
                italic = "Italic" in char.fontname
                if italic and not i0:
                    linetext.append("<em>")
                elif i0 and not italic:
                    linetext.append("</em>")

                linetext.append(char.get_text())

        wasbq = blockquote

        linetext = "".join(linetext).strip()

        # end last footnote
        if new_para and paragraphs[-1][0] == "[" and paragraphs[-1][1].isdigit(): #]
            footnotes.append(paragraphs[-1])
            del paragraphs[-1]

        first = False

        # start new paragraph
        if (new_para and ignore == 0) or refn is None:
            p = paragraphs[-1]
            if p.startswith("<quote>") and not p.endswith("</quote>"):
                paragraphs[-1] += "</quote>"
            if blockquote:
                linetext = "<quote>" + linetext
            paragraphs.append(linetext)
        else:
            p = paragraphs[-1]
            if p[-1] == "-":
                paragraphs[-1] = p[:-1] + linetext
            else:
                paragraphs[-1] += linetext if ignore == 2 else (" " + linetext)

            if ignore > 0: ignore -= 1

    footnote_total = len(footnotes)

print("Footnotes")
paragraphs.extend(footnotes)

print("Joining paragraphs")
content = "\n\n".join(paragraphs)

print("Replacements")
content = (content
        # hacks for exceptions that only happen one and so i am too lazy to propely fix
        .replace("reconnaissance</quote>\n\n<quote>ones", "reconnaissance ones")
        .replace("ISLANDS IN THE NET ", "ISLANDS IN THE NET\n\n")
        .replace("“only a begin-</quote>\n\n<quote>ning”", "“only a beginning”")
        .replace("loosely in-</quote>\n\n<quote>to national", "loosely into national")
        .replace("*** IV. Networked Resistance as an Example\n\n*** of Distributed Infrastructure",
            "*** IV. Networked Resistance as an Example of Distributed Infrastructure")
        .replace("*** IX. Networked, Distributed Successors to the State: Saint-\n\n*** Simon, Proudhon and “the Administration of Things”",
            "*** IX. Networked, Distributed Successors to the State: Saint-Simon, Proudhon and “the Administration of Things”")
        .replace("** 5. Basic Infrastructures: Networked Economies\n\n** and Platform",
            "** 5. Basic Infrastructures: Networked Economies and Platform")
        .replace("** 7. Basic Infrastructures: Education and\n\n** Credentialing",
            "** 7. Basic Infrastructures: Education and Credentialing")
        .replace("*** III. Networked Certification, Reputational\n\n*** and Verification Mechanisms.",
            "*** III. Networked Certification, Reputational and Verification Mechanisms.")
        .replace("*** III. Active Defense, Counter-Terrorism, and\n\n*** Other Security Against Attack.",
            "*** III. Active Defense, Counter-Terrorism, and Other Security Against Attack.")
        .replace("*** XII. Networked Labor Organizations and Guilds\n\n*** as Examples of Phyles",
                "*** XII. Networked Labor Organizations and Guilds as Examples of Phyles")
        .replace("** Appendix. Case Study in Networked Resistance:\n\n** From Wikileaks to Occupy—and Beyond",
            "** Appendix. Case Study in Networked Resistance: From Wikileaks to Occupy—and Beyond")
        # add <biblio> around bibliography
        .replace("** Bibliography\n\n", "** Bibliography\n\n<biblio>\n")
        .replace("\n\n[1] See Kevin Carson", "\n</biblio>\n\n[1] See Kevin Carson")
        # ...
        .replace(". . . . .", ".....")
        .replace(". . . .", "....")
        .replace(". . .", "...")

        .replace("</quote>\n\n<quote>", "\n\n")
        .replace("•\n\n", "\n\n• ")
        .replace(" • ", "\n\n - ")
        .replace("\n\n• ", "\n\n - ")
        .replace("<quote>• ", "<quote>\n - ")
        .replace("<em> </em>", " ")
        .replace(" </em>", "</em> "))

# It is individuals, not companies who do Enterprise 2.0.[220]

with open('out.muse', 'w') as f:
    print("Writing")
    f.write(content)
