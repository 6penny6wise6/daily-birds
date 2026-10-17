# Bird of the Day

Live page: https://6penny6wise6.github.io/daily-birds/

Every day the page shows one bird: a real photo, its name, a "did you know?" fact,
and a quick "guess before you scroll" question. Past birds show up under
"See past birds", and there's a share button.

## How it "posts" every day

Nothing has to run. The page reads `birds.json` and shows the entry for today's
date (Chicago time). Birds dated in the future stay hidden until their day comes.
If a day has no bird, the page shows the most recent one instead. So as long as
`birds.json` has birds lined up ahead, a new one appears every morning on its own.

## Add or change a day

**Easiest: ask the bot.** Tell it something like "put a Barn Owl on Oct 31" or
"swap tomorrow's bird for a flamingo". It finds a properly licensed photo, checks
the fact, and pushes the update.

**On GitHub, by hand:**

1. Open `birds.json` in the repo and click the pencil (Edit) icon.
2. Each bird is one block like this:

   ```json
   {
     "date": "2026-10-31",
     "name": "Barn Owl",
     "scientific": "Tyto alba",
     "photo": "photos/barn-owl.jpg",
     "photo_credit": "Photographer name",
     "photo_license": "CC BY-SA 4.0",
     "photo_source_url": "https://commons.wikimedia.org/wiki/File:...",
     "fact": "A short, true fun fact.",
     "source": "https://www.allaboutbirds.org/guide/Barn_Owl/",
     "question": "Optional quick question",
     "answer": "Optional answer"
   }
   ```

3. To change a day, edit its block. To remove a day, delete its block (and the
   comma that goes with it). To add one, copy a block and change it.
4. New photos go in the `photos/` folder (Add file → Upload files). Only use
   photos you're allowed to use, like Wikimedia Commons images marked CC BY,
   CC BY-SA, CC0 or public domain, and fill in the credit and license.
5. Click **Commit changes**. The live page updates in about a minute.

## The helper script

`add_bird.py` grabs a freely licensed photo from Wikimedia Commons, resizes it,
saves it in `photos/`, and writes the entry into `birds.json` (replacing that date
if it already has a bird).

```bash
# add or replace a day (photo found automatically from the bird's name)
python3 add_bird.py --date 2026-10-31 --name "Barn Owl" --scientific "Tyto alba" \
  --fact "Barn Owls can catch mice in complete darkness using hearing alone." \
  --source "https://www.allaboutbirds.org/guide/Barn_Owl/" \
  --question "How does a Barn Owl hunt in the dark?" --answer "By sound."

# pick a specific Commons photo instead
python3 add_bird.py --date 2026-10-31 --name "Barn Owl" --scientific "Tyto alba" \
  --fact "..." --photo-url "https://commons.wikimedia.org/wiki/File:Tyto_alba_-British_Wildlife_Centre,_Surrey,_England-8a_(1).jpg"

# remove a day
python3 add_bird.py --remove 2026-10-31

# add --push to any of these to commit and push in one go
```

It needs Python 3 and Pillow (`pip install pillow`). It refuses photos that aren't
CC BY, CC BY-SA, CC0 or public domain, and never uses AI-generated images.
