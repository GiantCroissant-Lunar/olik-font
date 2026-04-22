Snapshot source: `parsimonhi/animCJK` commit `2f469d33a8e78cf4d16dc61dccac1aa94d2cfcfe`

Files:
- `graphicsZhHant.txt`
- `dictionaryZhHant.txt`

Downloaded from:
- `https://raw.githubusercontent.com/parsimonhi/animCJK/master/graphicsZhHant.txt`
- `https://raw.githubusercontent.com/parsimonhi/animCJK/master/dictionaryZhHant.txt`

Committed subset:
- only rows whose `character` is present in upstream animCJK zh-Hant but absent
  from the committed MMH snapshot
- current set: `々 〇 喫 嵗 敎 榦 眞 箇 舘 証 説 鈡 麪 齣 𡻕`

This keeps the checked-in fallback data under the repo's file-size guard while
still recording authentic animCJK rows for every current zh-Hant fallback char.
