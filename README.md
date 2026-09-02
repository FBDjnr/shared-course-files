# Shared Course Files

Data files for my courses, each in its own folder, published so they can be read
straight from a URL without downloading anything first.

## Reading a file

Every file has a **raw** URL that returns its contents directly. In R:

```r
scores <- read.csv("https://raw.githubusercontent.com/FBDjnr/shared-course-files/main/msbr70200/example.csv")
```

In Python:

```python
import pandas as pd
scores = pd.read_csv("https://raw.githubusercontent.com/FBDjnr/shared-course-files/main/msbr70200/example.csv")
```

Use the `raw.githubusercontent.com` address, not the `github.com/.../blob/...` one
you see in the browser address bar. The browser URL returns the web page around
the file, so `read.csv()` on it fails with a parse error rather than giving you
the data.

## Finding a file

`index.csv` at the top level lists every shared file and its URL. It is itself a
CSV, so you can read it the same way:

```r
files <- read.csv("https://raw.githubusercontent.com/FBDjnr/shared-course-files/main/index.csv")

# Everything available for one course
subset(files, course == "msbr70200")

# Load a file by name, without hard-coding its URL
scores <- read.csv(files$url[files$file == "example.csv"])
```

Each course folder also carries its own `index.csv` covering just that course.

| Column | Meaning |
| --- | --- |
| `course` | Course folder the file belongs to |
| `file` | File name |
| `path` | Path within the repository |
| `type` | File extension, lower case |
| `bytes` | File size |
| `updated` | Date the file last changed |
| `url` | Raw URL to read the file from |

## Adding files

Put the file in the relevant course folder and push. To start a new course,
create a folder named for it and add files inside.

The indexes rebuild automatically: a GitHub Action runs on every push and commits
any change to `index.csv`. Nothing needs to be updated by hand, and the URLs it
writes are always the ones matching the current repository and branch.

To rebuild them locally, from anywhere in the repository:

```
python tools/build_index.py
```

Add `--check` to test whether they are current without writing anything, which is
useful before pushing.

## After you push, allow five minutes

Raw URLs are served through a cache with `max-age=300`. For up to five minutes
after a file changes, the old contents can still come back. Nothing is wrong; wait
and read again.

This matters most when correcting a file mid-class. If people need the new version
immediately, adding a query string defeats the cache:

```r
d <- read.csv(paste0(url, "?v=", as.integer(Sys.time())))
```

## Notes

Files here are readable by anyone with the address, since a public repository is
what makes plain `read.csv(url)` work. Do not put anything confidential in it:
no student names, grades, identifiers, or unpublished data covered by a licence.

Anything with a `.csv` extension is served as plain text. Large files are better
compressed, and anything over 100 MB is refused by GitHub.
