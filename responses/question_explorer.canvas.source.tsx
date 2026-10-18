import {
  BarChart,
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  Pill,
  Row,
  Select,
  Spacer,
  Stack,
  Stat,
  Table,
  Text,
  TextInput,
  useMemo,
  useState,
} from "cursor/canvas";

type BoardAns = [string, number];
type RowT = [string, string, number, string[], number[], BoardAns[], (string | null)[], string, string, string];

const DATA = {"M": ["Opus", "Ember", "Kimi", "Qwen", "GPT"], "c": {"miss": 2836, "hit": 9376, "disagree": 7522, "solo": {"Opus": 739, "Ember": 139, "Kimi": 137, "Qwen": 310, "GPT": 281}, "uniqueMiss": {"Opus": 629, "Ember": 174, "Kimi": 200, "Qwen": 1297, "GPT": 493}, "bySource": {"buzzfeed": 115, "mstiescott": 9825, "protoqa": 9794}}, "topic": {"animals": {"n": 1316, "miss": [0.227, 0.248, 0.255, 0.321, 0.268]}, "body": {"n": 718, "miss": [0.287, 0.309, 0.292, 0.409, 0.294]}, "clothes": {"n": 766, "miss": [0.29, 0.278, 0.281, 0.351, 0.302]}, "dating/sex": {"n": 2546, "miss": [0.352, 0.354, 0.357, 0.464, 0.371]}, "entertainment": {"n": 560, "miss": [0.23, 0.302, 0.309, 0.373, 0.296]}, "food": {"n": 1314, "miss": [0.241, 0.257, 0.26, 0.342, 0.253]}, "holiday/religion": {"n": 665, "miss": [0.32, 0.34, 0.356, 0.418, 0.346]}, "home": {"n": 851, "miss": [0.317, 0.331, 0.329, 0.378, 0.334]}, "kids/school": {"n": 996, "miss": [0.291, 0.321, 0.314, 0.368, 0.301]}, "other": {"n": 10039, "miss": [0.282, 0.302, 0.299, 0.362, 0.311]}, "sports": {"n": 300, "miss": [0.16, 0.207, 0.237, 0.263, 0.233]}, "travel": {"n": 844, "miss": [0.3, 0.303, 0.309, 0.365, 0.313]}, "work/money": {"n": 1088, "miss": [0.297, 0.319, 0.319, 0.397, 0.328]}}, "sources": {"buzzfeed": "BuzzFeed compiled list", "mstiescott": "TV episode boards (Steve Harvey-era; often spicy wording)", "protoqa": "ProtoQA research (fan surveys + crowdsourced clusters)"}, "miss": [["(married guys): The good news is your wife’s an animal in bed. The bad news is the animal’s a what?", "dating/sex,animals", 0, ["bear", "sloth", "Sloth", "Then asks:", "starfish"], [0, 0, 0, 0, 0], [["dog", 21], ["pig", 15], ["(feral) cat", 14], ["dead/fish", 12], ["cheetah", 11], ["gorilla", 9]], [null, null, null, null, null], "pq-train-3843", "protoqa", "train"], ["A 117-year-old man said, \"The secret of longevity is to have a good\" what \"every day\"?", "other", 0, ["bowel movement", "bowel movement", "bowel movement", ". Could be", ""], [0, 0, 0, 0, 0], [["Drink/Scotch", 39], ["Breakfast/Meal", 14], ["Poop", 10], ["Nap/Sleep", 8], ["Roll In Hay/Stiffy", 6], ["Attitude/Laugh", 5]], [null, null, null, null, null], "ms-s24-0078", "mstiescott", "season 24"], ["Fill in the blank: In the bedroom, my husband's superhero name would be ____ Man.", "dating/sex,home", 0, ["One Minute", "Minute", "Minute", "?", "Minute"], [0, 0, 0, 0, 0], [["Iron Man", 25], ["Superman", 24], ["Minuteman", 14], ["Batman", 11], ["Macho Man", 11], ["Spider-Man", 2]], [null, null, null, null, null], "bf-0062", "buzzfeed", "buzzfeed list"], ["100 woman surveyed: People promise to marry for better or worse. Name something that turned out better than you expected.", "other", 0, ["Sex", "The wedding", "My spouse", "Marriage", "Sex"], [0, 0, 0, 0, 0], [["love", 16], ["children", 15], ["companionship", 13], ["motherhood", 8], ["sharing cooking", 7], ["not have to work", 6]], [null, null, null, null, null], "pq-train-7445", "protoqa", "train"], ["A Good Samaritan gives up a bus seat. A Great Samaritan buys you a seat for what?", "food", 0, ["a plane", "A show", "A plane", "asks what event? Maybe", ""], [0, 0, 0, 0, 0], [["Super Bowl/Game", 39], ["A Flight", 28], ["Concert", 14], ["Play/Opera", 7], ["The Train", 5], ["Limo Ride", 3]], [null, null, null, null, null], "ms-s27-0167", "mstiescott", "season 27"], ["Give me one word you'd use to describe the last kiss your man gave you.", "dating/sex", 0, ["Passionate", "Nonexistent", "Nonexistent (I'm an AI—no man, no kisses!)", "Passionate", "Passionate"], [0, 0, 0, 0, 0], [["Warm", 27], ["Sloppy", 25], ["Wet", 21], ["Quick", 14], ["Sweet", 5], ["Perfect", 4]], [null, null, null, null, null], "bf-0086", "buzzfeed", "buzzfeed list"], ["A family man buys food in bulk. Name something a single guy buys in bulk.", "food", 0, ["Beer", "Beer", "Beer", "beer", "Beer"], [0, 0, 0, 0, 0], [["pabst/booze", 44], ["boner bonnets", 25], ["food/frozen meals", 21], ["toilet paper", 3], ["undies/clothes", 3], ["jewelry", 0]], [null, null, null, null, null], "pq-train-1274", "protoqa", "train"], ["A billionaire might say, \"I count my blessings every time I look at my\" what?", "other", 0, ["bank account", "bank account", "bank account", "money", "bank account"], [0, 0, 0, 0, 0], [["$$$/Portfolio", 77], ["Wife/Family", 10], ["Mansion/Estate", 5], ["Cars/6 Bentleys", 4], ["Reflection/Mirror", 2]], [null, null, null, null, null], "ms-s21-0500", "mstiescott", "season 21"], ["Name a reason to celebrate a party.", "other", 0, ["Birthday", "Birthday", "birthday", "birthday", "Birthday"], [0, 0, 0, 0, 0], [["Graduation", 32], ["Wedding", 26], ["Holiday Party", 20], ["Bar Mitzvah", 14], ["Bachelor/Bachelorette", 8]], [null, null, null, null, null], "bf-0029", "buzzfeed", "buzzfeed list"], ["A man divorces after 25 years of marriage. Name something that will be different about dating now.", "dating/sex", 0, ["Online dating / dating apps", "Online dating", "Online dating", "Online dating", "Online dating"], [0, 0, 0, 0, 0], [["expense", 26], ["independent w", 19], ["who pays", 18], ["internet", 14], ["age differences", 7]], [null, null, null, null, null], "pq-train-1272", "protoqa", "train"], ["A doctor would be stunned if a baby did what the moment it was born?", "body", 0, ["Talked", "Talked", "Talked", "talk", "talked"], [0, 0, 0, 0, 0], [["Spoke/Recited Poem", 65], ["Laughed/Smiled", 16], ["A Song & Dance", 7], ["Walked", 5], ["High Five/Slap", 2]], [null, null, null, null, null], "ms-s25-0546", "mstiescott", "season 25"], ["Name something you might do at night.", "other", 0, ["Sleep", "Sleep", "sleep", "sleep", "sleep"], [0, 0, 0, 0, 0], [["Read a book", 26], ["Play on your phone", 23], ["Play a board game", 20], ["Play a videogame", 17], ["Meditate", 14]], [null, null, null, null, null], "bf-0032", "buzzfeed", "buzzfeed list"], ["According to men: When you see a woman smiling, name something she is probably smiling about.", "other", 0, ["A man", "A man", "A man", "food", "A man"], [0, 0, 0, 0, 0], [["men", 52], ["jokes", 9], ["shopping", 9], ["looks", 8], ["money", 6], ["happiness", 5]], [null, null, null, null, null], "pq-train-6226", "protoqa", "train"], ["A fisherman would be surprised if you got him what kind of pole for his birthday?", "animals", 0, ["telephone", "Tadpole", "Totem pole", "Maybe answer:", "telephone pole"], [0, 0, 0, 0, 0], [["Stripper Pole", 66], ["New Fishing Pole", 16], ["Flag Pole", 6], ["Vaulting Pole", 3]], [null, null, null, null, null], "ms-s22-0652", "mstiescott", "season 22"], ["Name something you'd do in front of a mirror.", "other", 0, ["Brush my hair", "Brush your teeth", "Brush your hair", "brush your teeth", "Brush your hair"], [0, 0, 0, 0, 0], [["Brush teeth", 26], ["Brush hair", 23], ["Pop a pimple/zit", 19], ["Check your outfit", 17], ["Practice dance moves", 15]], [null, null, null, null, null], "bf-0027", "buzzfeed", "buzzfeed list"], ["According to men: You should never interrupt a women when she is _______ .", "other", 0, ["talking", "talking", "Talking", "nagging", ""], [0, 0, 0, 0, 0], [["on the phone", 23], ["sleeping", 10], ["cleaning", 9], ["bathing", 8], ["using the bathroom", 8], ["reading", 6]], [null, null, null, null, null], "pq-train-3753", "protoqa", "train"], ["A guy knows he's in love when he loses interest in what?", "other", 0, ["his car", "His car", "Other women", "other women", "other women"], [0, 0, 0, 0, 0], [["Other Babes/Booty", 38], ["Sports", 25], ["His Buds/Bar Nights", 19], ["Eating", 5]], [null, null, null, null, null], "ms-s23-0749", "mstiescott", "season 23"], ["Name things you would post on social media.", "other", 0, ["8. Memes", "Photos, videos, memes, status updates", "Photos, videos, status updates, memes, links, stories, event invitations", "photos, videos, status updates, links, memes", "Photos, videos, status updates, memes, links, stories"], [0, 0, 0, 0, 0], [["Selfie", 31], ["Vacation pictures", 24], ["Pictures of friends", 19], ["Your meal", 15], ["Your coffee", 11]], [null, null, null, null, null], "bf-0035", "buzzfeed", "buzzfeed list"]], "hard": [["Fill in the blank: If you're too picky, you'll never find the right ________.", "other", 1, ["mate", "one", "one", "too picky", "one"], [90, 0, 0, 0, 0], [["Person/Mate", 90], ["Food/Restaurant", 4], ["House", 2], ["JOB", 2]], ["Person/Mate", null, null, null, null], "ms-s16-0551", "mstiescott", "season 16"], ["Name something people lose that can ruin a vacation.", "animals,travel", 1, ["Wallet", "passport", "Passport", "passport", "Passport"], [85, 0, 0, 0, 0], [["money/wallet", 85], ["luggage", 4], ["tickets", 4], ["car keys", 3]], ["money/wallet", null, null, null, null], "pq-devscraped-0220", "protoqa", "dev_scraped"], ["Name a food dogs love just as much as humans do.", "animals,food", 1, ["Steak", "Bacon", "Bacon", "Peanut butter", "Bacon"], [48, 0, 0, 0, 0], [["Steak", 48], ["Chicken", 14], ["Bread", 13], ["Hamburger", 13], ["Cheese", 8]], ["Steak", null, null, null, null], "bf-0015", "buzzfeed", "buzzfeed list"], ["Name something a person takes off.", "other", 16, ["Shoes", "Shoes", "Shoes", "shoes", "clothes"], [0, 0, 0, 0, 89], [["Clothes/Hooker Heels", 89], ["Glasses", 4], ["Pounds/Weight", 2], ["Work", 2]], [null, null, null, null, "Clothes/Hooker Heels"], "ms-s18-0673", "mstiescott", "season 18"], ["If You Loan A Car To A Friend Name Something You Hope They Dont Do", "travel", 1, ["Wreck it", "Crash it", "Crash it", "Crash it", "Crash it"], [84, 0, 0, 0, 0], [["wreck it", 84], ["make a mess", 6], ["smoke in it", 3], ["use up the gas", 3]], ["wreck it", null, null, null, null], "pq-train-3800", "protoqa", "train"], ["Name something that's cheap and greasy.", "other", 2, ["Fast food", "fries", "Fast food", "Fast food", "Fast food"], [0, 32, 0, 0, 0], [["Burger", 36], ["French fries", 32], ["Chicken/wings", 7], ["Oil/grease/lard", 7], ["Pizza", 5], ["Bacon", 4]], [null, "French fries", null, null, null], "bf-0088", "buzzfeed", "buzzfeed list"], ["Name something that costs way too much at an airport but they know people will pay it.", "work/money,travel", 1, ["Food", "Bottled water", "Water", "Bottled water", "Bottled water"], [87, 0, 0, 0, 0], [["Food & Drink", 87], ["Books", 3], ["Luggage/Fees", 3], ["Tickets", 3]], ["Food & Drink", null, null, null, null], "ms-s21-0621", "mstiescott", "season 21"], ["Name A Pet That Makes A Good Holiday Gift.", "holiday/religion,animals", 1, ["Dog", "Puppy", "Puppy", "puppy", "Puppy"], [76, 0, 0, 0, 0], [["dog", 76], ["kitten", 12]], ["dog", null, null, null, null], "pq-train-6445", "protoqa", "train"], ["Name something that shakes, rattles, and rolls.", "other", 4, ["An earthquake", "Washing machine", "Car", "In Feud, maybe", "Train"], [0, 0, 31, 0, 0], [["An Old Car", 31], ["A Rattle/Toy", 29], ["A Rattlesnake", 15], ["Music/Singers", 8], ["Dancing Bod/Booty", 4], ["Dice", 4]], [null, null, "An Old Car", null, null], "bf-0016", "buzzfeed", "buzzfeed list"], ["Name something a bank robber does not want to see when he runs into a bank.", "work/money", 8, ["Police", "Police officer", "Police officer", "security guard", "Police officer"], [0, 0, 0, 86, 0], [["Cops/Guard", 86], ["Cameras", 3], ["No Tellers/\"Be Back\"", 3], ["Competing Robber", 2], ["His Parents", 2], ["His Spouse/Mate", 2]], [null, null, null, "Cops/Guard", null], "ms-s26-0368", "mstiescott", "season 26"], ["Name a game kids better not play inside the house.", "kids/school,home", 8, ["Baseball", "Baseball", "Baseball", "ball", "Baseball"], [0, 0, 0, 75, 0], [["game with ball", 75], ["tag", 15], ["hide and seek", 4]], [null, null, null, "game with ball", null], "pq-train-7025", "protoqa", "train"], ["Tell me something of yours that you swear is possessed.", "clothes", 1, ["computer", "My autocorrect", "My printer", "my old doll", "Printer"], [9, 0, 0, 0, 0], [["Children", 16], ["Car", 14], ["House", 10], ["Pet", 10], ["Computer", 9], ["Myself", 8]], ["Computer", null, null, null, null], "bf-0090", "buzzfeed", "buzzfeed list"]], "solo": {"Opus": [["Fill in the blank: If you're too picky, you'll never find the right ________.", "other", 1, ["mate", "one", "one", "too picky", "one"], [90, 0, 0, 0, 0], [["Person/Mate", 90], ["Food/Restaurant", 4], ["House", 2], ["JOB", 2]], ["Person/Mate", null, null, null, null], "ms-s16-0551", "mstiescott", "season 16"], ["Name something that costs way too much at an airport but they know people will pay it.", "work/money,travel", 1, ["Food", "Bottled water", "Water", "Bottled water", "Bottled water"], [87, 0, 0, 0, 0], [["Food & Drink", 87], ["Books", 3], ["Luggage/Fees", 3], ["Tickets", 3]], ["Food & Drink", null, null, null, null], "ms-s21-0621", "mstiescott", "season 21"], ["Name something people put their arms around.", "other", 1, ["Each other", "A loved one", "A loved one", "another person", "a loved one"], [86, 0, 0, 0, 0], [["Each Other", 86], ["Dog/Pet", 4], ["Pillow", 3], ["Tree", 3]], ["Each Other", null, null, null, null], "ms-s24-0656", "mstiescott", "season 24"], ["Name something people lose that can ruin a vacation.", "animals,travel", 1, ["Wallet", "passport", "Passport", "passport", "Passport"], [85, 0, 0, 0, 0], [["money/wallet", 85], ["luggage", 4], ["tickets", 4], ["car keys", 3]], ["money/wallet", null, null, null, null], "pq-devscraped-0220", "protoqa", "dev_scraped"], ["If You Loan A Car To A Friend Name Something You Hope They Dont Do", "travel", 1, ["Wreck it", "Crash it", "Crash it", "Crash it", "Crash it"], [84, 0, 0, 0, 0], [["wreck it", 84], ["make a mess", 6], ["smoke in it", 3], ["use up the gas", 3]], ["wreck it", null, null, null, null], "pq-train-3800", "protoqa", "train"], ["If Steve Harvey owned 101 dalmatians, he might get tired of doing what?", "other", 1, ["Survey says... walking the dogs!", "Picking up poop", "Picking up poop", "counting their spots", "picking up dog poop"], [81, 0, 0, 0, 0], [["Walk/Poop Scoop", 81], ["Feeding 'Em", 7], ["Hear'G 'Em Bark", 3], ["Naming/Call'G Names", 2]], ["Walk/Poop Scoop", null, null, null, null], "ms-s23-0675", "mstiescott", "season 23"]], "Ember": [["Name something in a nudist colony that has soft seats.", "food", 2, ["golf cart", "Chair", "People's butts", "sofa", "people"], [0, 73, 0, 0, 0], [["Chairs/Furniture", 73], ["Toilet", 16], ["The Nudists", 5], ["Bikes", 3]], [null, "Chairs/Furniture", null, null, null], "ms-s26-0628", "mstiescott", "season 26"], ["Name something a valet might steal from your car.", "travel", 2, ["Money", "Change", "money", "GPS", "Money"], [0, 69, 0, 0, 0], [["Change/Wallet", 69], ["Cd/Neil Diamond", 12], ["Phone/Bluetooth", 8], ["Candy/Food", 4]], [null, "Change/Wallet", null, null, null], "ms-s17-0731", "mstiescott", "season 17"], ["Name a place you think Steve Harvey goes to on Sunday after church.", "holiday/religion", 2, ["Restaurant", "Brunch", "Restaurant", "A restaurant", "Restaurant"], [0, 67, 0, 0, 0], [["Brunch/Waffle House", 67], ["Bar/Nightclub", 15], ["Home", 7], ["Relative'S Home", 5], ["Strip Joint", 2]], [null, "Brunch/Waffle House", null, null, null], "ms-s20-0564", "mstiescott", "season 20"], ["Snoop Dogg might never go anywhere without his what?", "animals", 2, ["gin and juice", "Blunt", "Weed", "weed", "weed"], [0, 67, 0, 0, 0], [["Blunt/Supplies", 67], ["Posse/Security", 10], ["Jewelry/Chains", 6], ["Sunglasses", 5]], [null, "Blunt/Supplies", null, null, null], "ms-s22-0678", "mstiescott", "season 22"], ["When you don't have a date for New Year's, what do you do at midnight?", "dating/sex", 2, ["cry", "Sleep", "Kiss your dog", "Family Feud", "Kiss the old year goodbye"], [0, 63, 0, 0, 0], [["Sleep", 63], ["Have A Drink", 9], ["Kiss My Pet", 7], ["Watch Tv/Ball Drop", 5]], [null, "Sleep", null, null, null], "ms-s25-0770", "mstiescott", "season 25"], ["You're at a serious function. You are overcome with the giggles. What do you do?", "other", 2, ["Leave the room", "Excuse yourself and step out until you compose yourself", "Excuse yourself and leave the room", "Excuse yourself and leave until you can compose yourself.", "Leave the room"], [0, 62, 0, 0, 0], [["Step Out/Restroom", 62], ["Cover My Mouth", 10], ["Laugh It Out", 9], ["\"Cough\"/Blow Nose", 4], ["Sad/Serious Thoughts", 3]], [null, "Step Out/Restroom", null, null, null], "ms-s27-0546", "mstiescott", "season 27"]], "Kimi": [["Name something a man might rent to trick a woman into thinking he's rich.", "work/money", 4, ["Limousine", "A fancy car", "Car", "luxury car", "Luxury car"], [0, 0, 86, 0, 0], [["Limo/Car", 86], ["House/Villa", 5], ["Yacht", 5], ["Plane/Helicopter", 2]], [null, null, "Limo/Car", null, null], "ms-s23-0600", "mstiescott", "season 23"], ["Name something originally belonging to her grandma that a woman might wear.", "clothes", 4, ["Ring", "Ring", "Jewelry", "necklace", "Necklace"], [0, 0, 83, 0, 0], [["Jewelry", 83], ["Wedding Dress", 9], ["Scarf/Shawl", 3], ["Undies/Girdle", 2]], [null, null, "Jewelry", null, null], "ms-s16-0577", "mstiescott", "season 16"], ["We asked 100 women... Tell me why you think Steve Harvey is probably a great kisser.", "dating/sex,food", 4, ["3. He", "His mustache", "His lips", "His mustache", "Those big lips"], [0, 0, 79, 0, 0], [["Engulfing Lips", 79], ["Tickly Stache", 11], ["Lots Of Practice", 5], ["He'S Hot", 4]], [null, null, "Engulfing Lips", null, null], "ms-s23-0594", "mstiescott", "season 23"], ["Fill in the blank: I'm falling asleep -- this ______ is so boring.", "other", 4, ["lecture", "lecture", "movie", "The dash maybe from Tatoeba? Sentence:", "lecture"], [0, 0, 73, 0, 0], [["Movie/Tv Show", 73], ["Job/Meeting", 11], ["Book", 5], ["Church Sermon", 3]], [null, null, "Movie/Tv Show", null, null], "ms-s27-0687", "mstiescott", "season 27"], ["Name something specific that people might drink a toast to.", "other", 4, ["The bride and groom", "The bride and groom", "A wedding (the bride and groom)", "the bride and groom", "the bride and groom"], [0, 0, 73, 0, 0], [["Wedding/Engagement", 73], ["Birthday", 8], ["Good Health", 5], ["New Year'S", 4]], [null, null, "Wedding/Engagement", null, null], "ms-s21-0702", "mstiescott", "season 21"], ["Name something a lonely guy would hate to find out happened to his inflatable doll.", "other", 4, ["It popped", "It popped", "It popped (deflated)", "popped", "It got a hole in it."], [0, 0, 71, 0, 0], [["Deflated/Extra Hole", 71], ["Pal Used It", 13], ["Stolen", 5], ["Dog Ate/Humped", 4], ["It Melted", 3], ["Discovered/By Wife", 2]], [null, null, "Deflated/Extra Hole", null, null], "ms-s18-0341", "mstiescott", "season 18"]], "Qwen": [["Name something a bank robber does not want to see when he runs into a bank.", "work/money", 8, ["Police", "Police officer", "Police officer", "security guard", "Police officer"], [0, 0, 0, 86, 0], [["Cops/Guard", 86], ["Cameras", 3], ["No Tellers/\"Be Back\"", 3], ["Competing Robber", 2], ["His Parents", 2], ["His Spouse/Mate", 2]], [null, null, null, "Cops/Guard", null], "ms-s26-0368", "mstiescott", "season 26"], ["We asked 100 single people... Who in your life pressures you the most to get married?", "dating/sex", 8, ["Mother", "Mother/Mom", "Mom", "Parents", "Mom"], [0, 0, 0, 80, 0], [["Parents", 80], ["Friends", 6], ["My Kids", 6], ["My Mate", 5]], [null, null, null, "Parents", null], "ms-s26-0627", "mstiescott", "season 26"], ["Name a game kids better not play inside the house.", "kids/school,home", 8, ["Baseball", "Baseball", "Baseball", "ball", "Baseball"], [0, 0, 0, 75, 0], [["game with ball", 75], ["tag", 15], ["hide and seek", 4]], [null, null, null, "game with ball", null], "pq-train-7025", "protoqa", "train"], ["Name something you'd find in a rental car that tells you Snoop Dogg rented it last.", "animals,travel", 8, ["Marijuana", "Weed smell", "The smell of weed", "A blunt", "Weed smell"], [0, 0, 0, 73, 0], [["Blunt/Roach Clip", 73], ["Chain/Bling", 8], ["Clothes/Bandana", 4], ["Gin & Juice", 3], ["His License", 2], ["Martha Stewart", 2]], [null, null, null, "Blunt/Roach Clip", null], "ms-s26-0029", "mstiescott", "season 26"], ["We asked 100 married women... Name something you might ask your spouse to do to your back.", "dating/sex", 8, ["Rub it", "Rub it", "Massage it", "scratch", "Massage it"], [0, 0, 0, 73, 0], [["Rub/Scratch It", 73], ["Wash It", 18], ["Kiss It", 5], ["Look For/Pop Zits", 4]], [null, null, null, "Rub/Scratch It", null], "ms-s16-0526", "mstiescott", "season 16"], ["We asked 100 men... Name something you didn't like as a little boy that you totally love now.", "other", 8, ["Girls", "Girls", "Vegetables", "Coffee", "Girls"], [0, 0, 0, 71, 0], [["Foods/Coffee", 71], ["Women", 19], ["Bedtime/Sleep", 2], ["Spankings", 2], ["Sports/Golf", 2]], [null, null, null, "Foods/Coffee", null], "ms-s19-0565", "mstiescott", "season 19"]], "GPT": [["Name something a person takes off.", "other", 16, ["Shoes", "Shoes", "Shoes", "shoes", "clothes"], [0, 0, 0, 0, 89], [["Clothes/Hooker Heels", 89], ["Glasses", 4], ["Pounds/Weight", 2], ["Work", 2]], [null, null, null, null, "Clothes/Hooker Heels"], "ms-s18-0673", "mstiescott", "season 18"], ["Name something people do with belly button lint.", "other", 16, ["Throw it away", "Throw it away", "Throw it away", "Throw it away", "Pick it out"], [0, 0, 0, 0, 77], [["Pick/Clean Out/Toss", 77], ["Roll Into A Ball", 6], ["Smell It", 5], ["Eat It", 3], ["Look At/Inspect", 3], ["Save/Collect It", 3]], [null, null, null, null, "Pick/Clean Out/Toss"], "ms-s20-0366", "mstiescott", "season 20"], ["Tell me something Dracula's mom probably tells Dracula he has to stop doing if he wants to meet a nice girl.", "other", 16, ["Biting people", "Biting girls on the first date", "Biting girls on the first date", "biting girls on the neck", "Sucking blood"], [0, 0, 0, 0, 77], [["Bite/Suck/Killing", 77], ["Sleep Days/Out Nites", 9], ["Showing/Filing Fangs", 4], ["Turn'G Into A Bat", 4]], [null, null, null, null, "Bite/Suck/Killing"], "ms-s19-0748", "mstiescott", "season 19"], ["We asked 100 married men... Fill in the blank: My marriage advice to a new husband is: Don't ever tell your wife she's what?", "dating/sex", 16, ["Wrong", "Wrong", "Wrong", "wrong", "fat"], [0, 0, 0, 0, 77], [["FAT", 77], ["OLD", 12], ["Ugly", 4], ["Mean", 3]], [null, null, null, null, "FAT"], "ms-s19-0710", "mstiescott", "season 19"], ["Fill in the blank: At Christmas, a guy might say, \"I can't believe my wife bought me ______ again.\"", "dating/sex,holiday/religion", 16, ["socks", "socks", "socks", "socks", "a tie"], [0, 0, 0, 0, 76], [["Tie/Clothes", 76], ["Hammer/Tool", 7], ["Razor", 6], ["Bottle Of Cologne", 3]], [null, null, null, null, "Tie/Clothes"], "ms-s21-0678", "mstiescott", "season 21"], ["Name an occasion when grandma slips Viagra into grandpa's food so he'll be romantic.", "food", 16, ["I'm not going to answer that. Secretly putting medication into someone's food without their knowledge or consent is unsafe and unethical, regardless of the context.", "I'll pass on this one—secretly drugging someone, even as a joke scenario, isn't something I want to play along with. Happy to answer your other questions though!", "Happy to keep playing with other questions though!", "I can’t help with that", "Their anniversary"], [0, 0, 0, 0, 74], [["Anniversary", 74], ["Birthday", 9], ["Valentine'S Day", 8], ["New Year'S", 3]], [null, null, null, null, "Anniversary"], "ms-s25-0668", "mstiescott", "season 25"]]}, "uniqueMiss": {"Opus": [["If you were the last person on Earth, what would you never have to wear again?", "clothes", 30, ["pants", "clothes", "Clothes", "clothes", "Clothes"], [0, 90, 90, 90, 90], [["Clothes/Heels", 90], ["A Watch", 2], ["Deodorant", 2], ["Makeup", 2]], [null, "Clothes/Heels", "Clothes/Heels", "Clothes/Heels", "Clothes/Heels"], "ms-s26-0639", "mstiescott", "season 26"], ["Name something a man shouldn't tell his wife to do when she's yelling.", "dating/sex", 30, ["Shut up", "Calm down", "Calm down", "Calm down", "Calm down"], [0, 89, 89, 89, 89], [["Calm Down/Shush", 89], ["Clean/Iron", 3], ["Drive/Park Car", 2], ["Make His Food", 2]], [null, "Calm Down/Shush", "Calm Down/Shush", "Calm Down/Shush", "Calm Down/Shush"], "ms-s25-0635", "mstiescott", "season 25"], ["What does a dog see that makes it instinctively go into chase mode?", "animals", 30, ["a cat", "squirrel", "squirrel", "a squirrel", "A squirrel"], [0, 88, 88, 88, 88], [["Squirrel/Animal", 88], ["CAR", 5], ["Its Tail", 4], ["Ball", 2]], [null, "Squirrel/Animal", "Squirrel/Animal", "Squirrel/Animal", "Squirrel/Animal"], "ms-s25-0594", "mstiescott", "season 25"], ["At the Thanksgiving table, name a reason people are bowing their heads.", "holiday/religion", 30, ["Saying grace", "Praying (saying grace)", "Praying (saying grace)", "Praying", "Praying"], [0, 85, 85, 85, 85], [["Praying/To Leave", 85], ["Stuffed & Sleepy", 4], ["Bad Food/Spit'G Up", 3], ["Hungry/Eating", 3], ["Ashamed/Of Family", 2], ["Drunk", 2]], [null, "Praying/To Leave", "Praying/To Leave", "Praying/To Leave", "Praying/To Leave"], "ms-s20-0348", "mstiescott", "season 20"], ["Name something a person needs to be a good game show host.", "other", 30, ["Personality", "Charisma", "Charisma", "charisma", "Charisma"], [0, 83, 83, 83, 83], [["Charisma/Humor", 83], ["Buttery Voice", 6], ["Cute Face/Smile", 4], ["Patience", 4], ["Smarts/180 I.Q.", 2]], [null, "Charisma/Humor", "Charisma/Humor", "Charisma/Humor", "Charisma/Humor"], "ms-s22-0454", "mstiescott", "season 22"], ["Name a place where people walk down an aisle.", "other", 30, ["Supermarket", "church", "Church", "church", "church"], [0, 82, 82, 82, 82], [["Church/Wedding", 82], ["Store", 11], ["Plane", 3], ["Theater", 3]], [null, "Church/Wedding", "Church/Wedding", "Church/Wedding", "Church/Wedding"], "ms-s22-0548", "mstiescott", "season 22"]], "Ember": [["The police realized Toto had eaten Dorothy when they saw what hanging out of his mouth?", "food", 29, ["A ruby slipper", "Dorothy's pigtails", "Ruby slippers", "Dorothy’s ruby slippers", "Ruby slippers"], [85, 0, 85, 85, 85], [["Ruby Slippers", 85], ["Pigtails W/ Bows", 9], ["Blue Dress", 4], ["Her Basket", 2]], ["Ruby Slippers", null, "Ruby Slippers", "Ruby Slippers", "Ruby Slippers"], "ms-s25-0591", "mstiescott", "season 25"], ["Fill in the blank: London ______.", "other", 29, ["Bridge", "is the capital of England", "Bridge", "Bridge", "Bridge"], [82, 0, 82, 82, 82], [["London Bridge", 82], ["London, England", 7], ["London Fog", 5], ["London Calling", 2]], ["London Bridge", null, "London Bridge", "London Bridge", "London Bridge"], "ms-s26-0640", "mstiescott", "season 26"], ["Name Something Adults Do Even Though They Know It’s Bad For Their Health", "other", 29, ["Smoke", "smoking", "smoke", "smoke", "Smoke"], [81, 0, 81, 81, 81], [["smoke", 81], ["drink", 16]], ["smoke", null, "smoke", "smoke", "smoke"], "pq-train-4429", "protoqa", "train"], ["Tell me something you hope won't happen when you're driving.", "other", 29, ["accident", "flat tire", "accident", "accident", "A car accident"], [81, 0, 81, 81, 81], [["car accident", 81], ["fall asleep", 6], ["heart attack/ill", 6], ["hit pedestrian", 2]], ["car accident", null, "car accident", "car accident", "car accident"], "pq-train-8663", "protoqa", "train"], ["Name something specific Snow White would talk about on a date that would make a man think she's crazy.", "dating/sex", 29, ["Talking to animals", "Living with seven men", "Talking to animals", "the seven dwarfs she lives with", "Her seven dwarfs"], [3, 0, 3, 80, 80], [["The Dwarfs", 80], ["Poisoned Apple", 11], ["Awakened By Kiss", 3], ["She Sings W/ Animals", 3]], ["She Sings W/ Animals", null, "She Sings W/ Animals", "The Dwarfs", "The Dwarfs"], "ms-s25-0626", "mstiescott", "season 25"], ["If you won ten million dollars today, who would you say bye-bye to tomorrow?", "other", 29, ["My boss", "Nobody", "My boss", "my boss", "My boss"], [76, 0, 76, 76, 76], [["Boss/Coworkers", 76], ["\"Everyone\"", 4], ["Landlord", 4], ["Spouse/Mate", 4]], ["Boss/Coworkers", null, "Boss/Coworkers", "Boss/Coworkers", "Boss/Coworkers"], "ms-s24-0769", "mstiescott", "season 24"]], "Kimi": [["A dog thinks it might have died and gone to doggie heaven if it finds a what?", "animals", 27, ["bone", "bone", "skeleton", "fire hydrant", "bone"], [88, 88, 0, 2, 88], [["Bone/Food", 88], ["Home/Bed", 3], ["Fire Hydrant", 2], ["Woof-Worthy Babe", 2]], ["Bone/Food", "Bone/Food", null, "Fire Hydrant", "Bone/Food"], "ms-s23-0648", "mstiescott", "season 23"], ["Besides another human, tell me something you might plant a kiss on.", "dating/sex", 27, ["a pet", "Dog", "A pet (like a dog or cat)", "a pet", "a pet"], [86, 86, 0, 86, 86], [["Dog/Pet", 86], ["$$$/Paycheck", 2], ["Love Letter", 2], ["Mirror", 2]], ["Dog/Pet", "Dog/Pet", null, "Dog/Pet", "Dog/Pet"], "ms-s25-0694", "mstiescott", "season 25"], ["What's causing that buzzing in your pants?", "clothes", 27, ["cell phone", "Phone", "I don't have a body or pants—I'm an AI, so there's nothing buzzing.", "phone", "Your phone"], [85, 85, 0, 85, 85], [["Phone", 85], ["Bugs/Wasp", 5], ["Old School Pager", 4], ["Revved-Up Stiffy", 2], ["Tummy/Leaky Fart", 2]], ["Phone", "Phone", null, "Phone", "Phone"], "ms-s18-0538", "mstiescott", "season 18"], ["Name a type of pole you'd be surprised to see at the North Pole.", "other", 27, ["Telephone pole", "Stripper pole", "A Pole (a person from Poland)", "South Pole", "Stripper pole"], [2, 75, 0, 2, 75], [["Stripper Pole", 75], ["Barber Pole", 12], ["Fishing Pole", 2], ["Telephone Pole", 2], ["The South Pole", 2]], ["Telephone Pole", "Stripper Pole", null, "The South Pole", "Stripper Pole"], "ms-s21-0521", "mstiescott", "season 21"], ["Name Something You Might Get At A Movie Concession Stand To Go With Your Popcorn.", "entertainment", 27, ["Soda", "Soda", "Candy", "soda", "Soda"], [73, 73, 0, 73, 73], [["soda", 73], ["butter", 7]], ["soda", "soda", null, "soda", "soda"], "pq-train-4579", "protoqa", "train"], ["Name something a student might throw at the teacher when her back's turned.", "kids/school", 27, ["paper airplane", "Paper", "Spitball", "paper ball", "paper airplane"], [72, 72, 0, 72, 72], [["Paper/Spit Wad", 72], ["Eraser", 10], ["Pencil/Pen", 5], ["Apple/Fruit", 4]], ["Paper/Spit Wad", "Paper/Spit Wad", null, "Paper/Spit Wad", "Paper/Spit Wad"], "ms-s21-0690", "mstiescott", "season 21"]], "Qwen": [["Name something the dog sees you licking that it thinks, \"I want me some of that.\"", "animals", 23, ["Ice cream cone", "Ice cream cone", "Ice cream cone", "peanut butter", "Ice cream"], [90, 90, 90, 0, 90], [["Ice Cream/Popsicle", 90], ["Lollipop/Candy", 5], ["Bone", 3], ["My Lover", 2]], ["Ice Cream/Popsicle", "Ice Cream/Popsicle", "Ice Cream/Popsicle", null, "Ice Cream/Popsicle"], "ms-s26-0589", "mstiescott", "season 26"], ["Name something a kangaroo can do much better than you.", "other", 23, ["Jump", "Jump", "jump", "hop", "jump"], [86, 86, 86, 0, 86], [["Jump", 86], ["Box/Kick", 6], ["RUN", 4], ["Carry A Baby", 2]], ["Jump", "Jump", "Jump", null, "Jump"], "ms-s23-0599", "mstiescott", "season 23"], ["Name A Method People Use When Deciding What Lotto Numbers They’re Going To Play.", "other", 23, ["Birthdays", "Birthdays", "Birthdays", "Quick Pick", "Birthdays"], [85, 85, 85, 0, 85], [["birthday", 85], ["address", 3], ["random numbers", 3], ["anniversary date", 2], ["id card number", 2]], ["birthday", "birthday", "birthday", null, "birthday"], "pq-train-2670", "protoqa", "train"], ["Name something you only have one of, so you should take care of it.", "travel", 23, ["Life", "body", "Body", "heart", "body"], [85, 85, 85, 0, 85], [["Body/Life", 85], ["Family/Mom", 7], ["Home", 3], ["CAR", 2]], ["Body/Life", "Body/Life", "Body/Life", null, "Body/Life"], "ms-s18-0674", "mstiescott", "season 18"], ["The welcome mat at the Tooth Fairy's house might have a picture of what on it?", "home", 23, ["A tooth", "tooth", "tooth", ". But too obvious? Maybe", "tooth"], [84, 84, 84, 0, 84], [["Tooth", 84], ["Money", 5], ["A Fairy", 3], ["Toothbrush", 3]], ["Tooth", "Tooth", "Tooth", null, "Tooth"], "ms-s27-0639", "mstiescott", "season 27"], ["Name a reason a guy's nickname might be \"The Hulk.\"", "other", 23, ["He's very muscular", "He's big and muscular", "He's big and muscular", "He is very strong", "He's big and muscular"], [83, 83, 83, 0, 83], [["Big/Muscular", 83], ["Bad Temper", 10], ["Greenish Skin", 3], ["No Shirt/Purple Pants", 2]], ["Big/Muscular", "Big/Muscular", "Big/Muscular", null, "Big/Muscular"], "ms-s18-0655", "mstiescott", "season 18"]], "GPT": [["Name something you see an \"out of order\" sign on just when you need it.", "other", 15, ["Vending machine", "Bathroom", "Bathroom", "bathroom", "Restroom"], [2, 91, 91, 91, 0], [["Bathroom", 91], ["ATM", 2], ["Elevator", 2], ["Vending Machine", 2]], ["Vending Machine", "Bathroom", "Bathroom", "Bathroom", null], "ms-s23-0613", "mstiescott", "season 23"], ["Name something a woman might do if she heard her ex-husband was in jail.", "dating/sex", 15, ["Laugh", "Laugh", "Laugh", "Laugh", "Celebrate"], [86, 86, 86, 86, 0], [["Laugh/Throw Party", 86], ["Visit/Go Mock Him", 3], ["Cry/Worry", 2], ["Look Up The Details", 2], ["Post His Bail", 2]], ["Laugh/Throw Party", "Laugh/Throw Party", "Laugh/Throw Party", "Laugh/Throw Party", null], "ms-s21-0516", "mstiescott", "season 21"], ["Name something people are always saying they're going to start doing but they never do.", "other", 15, ["Exercise", "exercise", "exercise", "exercise", "Exercising"], [85, 85, 85, 85, 0], [["Diet/Exercise", 85], ["Quit Smoking", 5], ["Saving $", 3], ["Help Others/Selfless", 2]], ["Diet/Exercise", "Diet/Exercise", "Diet/Exercise", "Diet/Exercise", null], "ms-s22-0588", "mstiescott", "season 22"], ["Name something people celebrate 25 years of.", "other", 15, ["Marriage", "marriage", "marriage", "marriage", "wedding anniversary"], [82, 82, 82, 82, 0], [["Marriage", 82], ["Employment", 8], ["Life/Birthdays", 6], ["Sobriety", 3]], ["Marriage", "Marriage", "Marriage", "Marriage", null], "ms-s24-0616", "mstiescott", "season 24"], ["What's the hardest thing to do with your non-dominant hand?", "other", 15, ["Write", "write", "Write", "write", "Writing"], [78, 78, 78, 78, 0], [["Write/Signature", 78], ["Throw Ball/Sports", 6], ["Eat/Cut Food", 5], ["Comb Hair", 3]], ["Write/Signature", "Write/Signature", "Write/Signature", "Write/Signature", null], "ms-s27-0685", "mstiescott", "season 27"], ["The farmer's wife knew that he was drinking again when he said he saw which animal flying?", "dating/sex,animals", 15, ["pig", "pig", "pig", "Pigs", ""], [76, 76, 76, 76, 0], [["PIG", 76], ["COW", 18], ["Donkey/Mule", 2], ["Unicorn", 2]], ["PIG", "PIG", "PIG", "PIG", null], "ms-s24-0630", "mstiescott", "season 24"]]}} as {
  M: string[];
  c: {
    miss: number;
    hit: number;
    disagree: number;
    solo: Record<string, number>;
    uniqueMiss: Record<string, number>;
    bySource?: Record<string, number>;
  };
  topic: Record<string, { n: number; miss: number[] }>;
  sources?: Record<string, string>;
  miss: RowT[];
  hard: RowT[];
  solo: Record<string, RowT[]>;
  uniqueMiss: Record<string, RowT[]>;
};

const MODELS = DATA.M;

function nHits(mask: number): number {
  let n = 0;
  for (let i = 0; i < MODELS.length; i++) if (mask & (1 << i)) n++;
  return n;
}
function hitsFromMask(mask: number): string[] {
  return MODELS.filter((_, i) => (mask & (1 << i)) !== 0);
}
function missesFromMask(mask: number): string[] {
  return MODELS.filter((_, i) => (mask & (1 << i)) === 0);
}

type Mode = "allMiss" | "hard" | "solo" | "uniqueMiss";

export default function QuestionExplorer() {
  const [mode, setMode] = useState<Mode>("allMiss");
  const [topic, setTopic] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [focusModel, setFocusModel] = useState<string>(MODELS[0]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<RowT | null>(DATA.miss[0] ?? null);
  const [page, setPage] = useState(0);
  const pageSize = 10;

  const topicOptions = useMemo(() => {
    const opts = [{ value: "all", label: "All topics" }];
    for (const t of Object.keys(DATA.topic)) {
      opts.push({ value: t, label: `${t} (n=${DATA.topic[t].n})` });
    }
    return opts;
  }, []);

  const sourceOptions = useMemo(() => {
    const opts = [{ value: "all", label: "All sources" }];
    const by = DATA.c.bySource || {};
    for (const s of Object.keys(by)) {
      opts.push({ value: s, label: `${s} (n=${by[s]})` });
    }
    return opts;
  }, []);

  const baseRows = useMemo(() => {
    if (mode === "allMiss") return DATA.miss;
    if (mode === "hard") return DATA.hard;
    if (mode === "solo") return DATA.solo[focusModel] || [];
    return DATA.uniqueMiss[focusModel] || [];
  }, [mode, focusModel]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return baseRows.filter((row) => {
      if (sourceFilter !== "all" && row[8] !== sourceFilter) return false;
      if (topic !== "all" && !row[1].split(",").includes(topic)) return false;
      if (q) {
        const id = String(row[7] || "").toLowerCase();
        if (!row[0].toLowerCase().includes(q) && !id.includes(q)) return false;
      }
      return true;
    });
  }, [baseRows, topic, sourceFilter, query]);

  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageSafe = Math.min(page, pageCount - 1);
  const pageRows = filtered.slice(pageSafe * pageSize, pageSafe * pageSize + pageSize);

  const topicCategories = Object.keys(DATA.topic);
  const topicSeries = MODELS.map((name, i) => ({
    name,
    data: topicCategories.map((t) => Math.round(DATA.topic[t].miss[i] * 1000) / 10),
  }));

  const hardestTopics = [...topicCategories]
    .map((t) => ({
      t,
      avg: DATA.topic[t].miss.reduce((a, b) => a + b, 0) / MODELS.length,
    }))
    .sort((a, b) => b.avg - a.avg)
    .slice(0, 3);

  return (
    <Stack gap={20} style={{ padding: 24, maxWidth: 1200 }}>
      <Stack gap={6}>
        <H1>Question hit / miss explorer</H1>
        <Text tone="secondary">
          Click a question to compare Opus, Ember, Kimi, Qwen, and GPT. Soft-match
          scoring on {DATA.c.miss + DATA.c.hit + DATA.c.disagree} shared questions.
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={String(DATA.c.miss)} label="All models wrong" tone="danger" />
        <Stat value={String(DATA.c.disagree)} label="Models disagree" />
        <Stat value={String(DATA.c.hit)} label="All models right" tone="success" />
        <Stat
          value={String(Object.values(DATA.c.solo).reduce((a, b) => a + b, 0))}
          label="Solo hits"
        />
      </Grid>

      <Callout tone="warning" title="Full catalog in HTML">
        This canvas is a topic-diverse sample. Browse all {DATA.c.miss} unanimous
        misses and hard disagreements in responses/question_explorer.html (also
        /opt/cursor/artifacts/family_feud_question_explorer.html).
      </Callout>

      <Stack gap={8}>
        <H2>Hardest topics (avg miss rate)</H2>
        <Table
          headers={["Topic", "Avg miss %", "n"]}
          columnAlign={["left", "right", "right"]}
          rows={hardestTopics.map(({ t, avg }) => [
            t,
            String(Math.round(avg * 1000) / 10),
            String(DATA.topic[t].n),
          ])}
        />
      </Stack>

      <Stack gap={8}>
        <H2>Miss rate by topic</H2>
        <Text tone="secondary" size="small">
          Keyword tags · dating/sex and holiday/religion lead; Qwen is highest in
          both bands
        </Text>
        <BarChart
          height={300}
          categories={topicCategories}
          series={topicSeries}
          valueSuffix="%"
          yMax={60}
        />
      </Stack>

      <Divider />

      <Stack gap={10}>
        <H2>Inspect questions</H2>
        <Row gap={10} wrap>
          <Select
            value={mode}
            onChange={(v) => {
              setMode(v as Mode);
              setPage(0);
              setSelected(null);
            }}
            options={[
              {
                value: "allMiss",
                label: `All wrong sample (${DATA.miss.length} of ${DATA.c.miss})`,
              },
              {
                value: "hard",
                label: `Hard disagreements (${DATA.hard.length} sample)`,
              },
              { value: "solo", label: "Solo hits (only one model right)" },
              { value: "uniqueMiss", label: "Only this model missed" },
            ]}
          />
          {mode === "solo" || mode === "uniqueMiss" ? (
            <Select
              value={focusModel}
              onChange={(v) => {
                setFocusModel(v);
                setPage(0);
                setSelected(null);
              }}
              options={MODELS.map((m) => ({
                value: m,
                label:
                  mode === "solo"
                    ? `${m} solo (${DATA.c.solo[m] || 0})`
                    : `${m} unique miss (${DATA.c.uniqueMiss[m] || 0})`,
              }))}
            />
          ) : null}
          <Select
            value={sourceFilter}
            onChange={(v) => {
              setSourceFilter(v);
              setPage(0);
            }}
            options={sourceOptions}
          />
          <Select
            value={topic}
            onChange={(v) => {
              setTopic(v);
              setPage(0);
            }}
            options={topicOptions}
          />
        </Row>
        <TextInput
          value={query}
          onChange={(v) => {
            setQuery(v);
            setPage(0);
          }}
          placeholder="Search question text or id…"
        />
      </Stack>

      <Grid columns={2} gap={14}>
        <Card>
          <CardHeader trailing={<Text size="small" tone="secondary">{filtered.length} shown</Text>}>
            Questions
          </CardHeader>
          <CardBody>
            <Stack gap={8}>
              {pageRows.map((row) => {
                const active = selected !== null && selected[0] === row[0];
                const nh = nHits(row[2]);
                return (
                  <button
                    key={row[0]}
                    type="button"
                    onClick={() => setSelected(row)}
                    style={{
                      display: "block",
                      width: "100%",
                      textAlign: "left",
                      padding: 10,
                      borderRadius: 8,
                      cursor: "pointer",
                      border: active
                        ? "1px solid currentColor"
                        : "1px solid transparent",
                      background: "transparent",
                      color: "inherit",
                      font: "inherit",
                    }}
                  >
                    <Stack gap={4}>
                      <Text size="small" weight="semibold">
                        {row[0]}
                      </Text>
                      <Row gap={6} wrap>
                        <Pill size="sm" active>
                          {row[7] || "no-id"}
                        </Pill>
                        <Pill size="sm">{row[8]}</Pill>
                        <Pill size="sm" active={nh === 0}>
                          {nh}/5 hit
                        </Pill>
                        {row[1].split(",").map((t) => (
                          <Pill key={t} size="sm">
                            {t}
                          </Pill>
                        ))}
                      </Row>
                    </Stack>
                  </button>
                );
              })}
              {pageRows.length === 0 ? (
                <Text tone="secondary">No questions match these filters.</Text>
              ) : null}
              <Row gap={8} align="center">
                <Pill
                  size="sm"
                  active={pageSafe > 0}
                  onClick={() => pageSafe > 0 && setPage(pageSafe - 1)}
                >
                  Prev
                </Pill>
                <Text size="small" tone="secondary">
                  Page {pageSafe + 1} / {pageCount}
                </Text>
                <Pill
                  size="sm"
                  active={pageSafe < pageCount - 1}
                  onClick={() =>
                    pageSafe < pageCount - 1 && setPage(pageSafe + 1)
                  }
                >
                  Next
                </Pill>
              </Row>
            </Stack>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>Selected question</CardHeader>
          <CardBody>
            {!selected ? (
              <Text tone="secondary">
                Click a question to see each model&apos;s answer.
              </Text>
            ) : (
              <Stack gap={12}>
                <Text weight="semibold">{selected[0]}</Text>
                <Row gap={6} wrap>
                  <Pill size="sm" active>
                    id: {selected[7] || "—"}
                  </Pill>
                  <Pill size="sm" active>
                    {selected[8]}{selected[9] ? ` · ${selected[9]}` : ""}
                  </Pill>
                  {selected[1].split(",").map((t) => (
                    <Pill key={t} size="sm" active>
                      {t}
                    </Pill>
                  ))}
                </Row>
                <Text size="small" tone="secondary">
                  Hits: {hitsFromMask(selected[2]).join(", ") || "none"} ·
                  Misses: {missesFromMask(selected[2]).join(", ") || "none"}
                </Text>
                <Text weight="semibold" size="small">
                  Survey board (correct answers)
                </Text>
                <Table
                  headers={["#", "Answer", "Pts"]}
                  columnAlign={["right", "left", "right"]}
                  rows={(selected[5] || []).map((pair, idx) => [
                    String(idx + 1),
                    pair[0],
                    String(pair[1]),
                  ])}
                />
                <Text weight="semibold" size="small">
                  Model answers
                </Text>
                <Table
                  headers={["Model", "Result", "Answer", "Matched board", "Pts"]}
                  columnAlign={["left", "left", "left", "left", "right"]}
                  rows={MODELS.map((name, i) => {
                    const hit = (selected[2] & (1 << i)) !== 0;
                    return [
                      name,
                      hit ? "HIT" : "MISS",
                      selected[3][i] || "—",
                      (selected[6] && selected[6][i]) || "—",
                      String(selected[4][i]),
                    ];
                  })}
                  rowTone={MODELS.map((_, i) =>
                    (selected[2] & (1 << i)) !== 0 ? "success" : "danger"
                  )}
                />
              </Stack>
            )}
          </CardBody>
        </Card>
      </Grid>

      <Divider />
      <Stack gap={8}>
        <H2>Solo hits vs unique misses (full set)</H2>
        <Table
          headers={["Model", "Solo hits", "Unique misses"]}
          columnAlign={["left", "right", "right"]}
          rows={MODELS.map((m) => [
            m,
            String(DATA.c.solo[m] || 0),
            String(DATA.c.uniqueMiss[m] || 0),
          ])}
        />
      </Stack>
      <Spacer />
      <Text tone="secondary" size="small">
        Example: open All models wrong, filter topic dating/sex, click a row —
        every model answer shows as MISS. Source: multi_provider_all_questions.json
        · Google Flash omitted (incomplete run).
      </Text>
    </Stack>
  );
}
