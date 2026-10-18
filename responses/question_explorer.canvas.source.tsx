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
type RowT = [string, string, number, string[], number[], BoardAns[], (string | null)[]];

const DATA = {"M": ["Opus", "Ember", "Kimi", "Qwen", "GPT"], "c": {"miss": 3520, "hit": 8635, "disagree": 7579, "solo": {"Opus": 782, "Ember": 165, "Kimi": 129, "Qwen": 383, "GPT": 303}, "uniqueMiss": {"Opus": 608, "Ember": 158, "Kimi": 198, "Qwen": 1202, "GPT": 469}}, "topic": {"animals": {"n": 1316, "miss": [0.258, 0.284, 0.292, 0.357, 0.302]}, "body": {"n": 718, "miss": [0.32, 0.338, 0.322, 0.435, 0.323]}, "clothes": {"n": 766, "miss": [0.325, 0.313, 0.326, 0.384, 0.339]}, "dating/sex": {"n": 2546, "miss": [0.425, 0.443, 0.453, 0.531, 0.461]}, "entertainment": {"n": 560, "miss": [0.254, 0.316, 0.332, 0.393, 0.314]}, "food": {"n": 1314, "miss": [0.264, 0.303, 0.303, 0.368, 0.295]}, "holiday/religion": {"n": 665, "miss": [0.371, 0.388, 0.412, 0.46, 0.405]}, "home": {"n": 851, "miss": [0.373, 0.385, 0.39, 0.427, 0.383]}, "kids/school": {"n": 996, "miss": [0.333, 0.351, 0.346, 0.389, 0.337]}, "other": {"n": 10039, "miss": [0.319, 0.335, 0.337, 0.394, 0.35]}, "sports": {"n": 300, "miss": [0.17, 0.24, 0.26, 0.273, 0.257]}, "travel": {"n": 844, "miss": [0.331, 0.352, 0.365, 0.41, 0.363]}, "work/money": {"n": 1088, "miss": [0.347, 0.372, 0.378, 0.431, 0.377]}}, "miss": [["(married guys): The good news is your wife’s an animal in bed. The bad news is the animal’s a what?", "dating/sex,animals", 0, ["bear", "sloth", "Sloth", "Then asks:", "starfish"], [0, 0, 0, 0, 0], [["dog", 21], ["pig", 15], ["(feral) cat", 14], ["dead/fish", 12], ["cheetah", 11], ["gorilla", 9]], [null, null, null, null, null]], ["100 woman surveyed: People promise to marry for better or worse. Name something that turned out better than you expected.", "other", 0, ["Sex", "The wedding", "My spouse", "Marriage", "Sex"], [0, 0, 0, 0, 0], [["love", 16], ["children", 15], ["companionship", 13], ["motherhood", 8], ["sharing cooking", 7], ["not have to work", 6]], [null, null, null, null, null]], ["A Good Samaritan gives up a bus seat. A Great Samaritan buys you a seat for what?", "food", 0, ["a plane", "A show", "A plane", "asks what event? Maybe", ""], [0, 0, 0, 0, 0], [["Super Bowl/Game", 39], ["A Flight", 28], ["Concert", 14], ["Play/Opera", 7], ["The Train", 5], ["Limo Ride", 3]], [null, null, null, null, null]], ["A bald guy might drop his toupee off at a hairdresser to have them do what to it?", "body,clothes", 0, ["style it", "Wash it", "Style it", "to have it cut", "style it"], [0, 0, 0, 0, 0], [["Wash/Fumigate", 60], ["Style/Cut/Perm", 31], ["Dye/Blond Tips", 7], ["Add More Hair", 2]], [null, null, null, null, null]], ["A bunch of pirates were relaxing at a nudist colony. Name something they might still be wearing.", "clothes", 0, ["An eye patch", "Eye patch", "Eye patch", "eye patch", "Eye patch"], [0, 0, 0, 0, 0], [["Eyepatches", 51], ["Pirate Hats", 20], ["Swords", 12], ["Earrings/Jewelry", 6], ["Hooks", 3], ["Parrots On Shoulders", 2]], [null, null, null, null, null]], ["A dog lifts one leg to tinkle. What does a man lift one leg to do?", "animals", 0, ["fart", "Fart", "Fart", "put on his trousers", "Put on pants"], [0, 0, 0, 0, 0], [["Let One Go", 25], ["Walk/Run/Climb", 22], ["Scratch/Adjust Junk", 13], ["Put Pants On", 7], ["Hop/Jump", 6], ["Get On Bike/Harley", 5]], [null, null, null, null, null]], ["Admit it -- you've fantasized about doing what to your boss?", "work/money", 0, ["Telling them off", "I don't have a boss — or fantasies.", "Punching them", "telling them off", "Telling them off"], [0, 0, 0, 0, 0], [["Kill/Run Over", 23], ["Smack/Punch", 22], ["Tell Off/Quit", 16], ["Fire/Get Him Fired", 12], ["Go To Pound Town", 8], ["Gag/Torture", 5]], [null, null, null, null, null]], ["Adult kids are sick of their parents asking, \"When are you going to\" what?", "kids/school", 0, ["Get married", "Get married", "get married", "get married", "get married"], [0, 0, 0, 0, 0], [["Get Hitched", 20], ["Pop Some Spawn", 18], ["Clean/Your Room", 17], ["Move The Hell Out", 14], ["Grow Up", 11], ["Get A Job", 7]], [null, null, null, null, null]], ["After a wild Christmas party, name something you might find hanging on the Christmas tree.", "holiday/religion", 0, ["Underwear", "Underwear", "Underwear", "a drunk", "Underwear"], [0, 0, 0, 0, 0], [["Panties/Clothes", 89], ["Booze/Cans", 4], ["Food/Candy Canes", 3], ["Condoms/Used", 2]], [null, null, null, null, null]], ["At the wild Hollywood party, the celebs were so stoned, they went home with the wrong what?", "home,entertainment", 0, ["spouse", "Spouses", "Partners", "wrong spouse", "spouse"], [0, 0, 0, 0, 0], [["Partner/Posse", 52], ["Car/Driver", 17], ["Clothes/Shoes", 14], ["Purse", 9], ["Award Statue", 6]], [null, null, null, null, null]], ["Besides CD’s, Name Something A Music Store Might Sell", "entertainment", 0, ["Musical instruments", "instruments", "Records", "vinyl records", "Musical instruments"], [0, 0, 0, 0, 0], [["dvd's", 45], ["mp3 players", 19]], [null, null, null, null, null]], ["Besides a car, name something with wheels that's kept in a garage.", "travel", 0, ["bicycle", "Bicycle", "Lawnmower", "bicycle", "Bicycle"], [0, 0, 0, 0, 0], [["bike", 44], ["lawn mower", 29], ["motorcycle", 19], ["wheelbarrow", 3]], [null, null, null, null, null]], ["If there were a Baby Olympics, tell me what one of the events might be.", "sports", 0, ["Crawling race", "Crawling race", "Crawling race", "crawling race", "Crawling race"], [0, 0, 0, 0, 0], [["Crawl/100-Meter", 57], ["Poo/Diaper Fill-Up", 8], ["Bottle Toss", 7], ["Crying/Screaming", 7], ["Best Nurser", 5], ["Spit-Up", 3]], [null, null, null, null, null]], ["A guy might get more dates after he buys a what?", "dating/sex", 0, ["new car", "car", "car", "car", "car"], [0, 0, 0, 0, 0], [["Sick Ride", 65], ["Outfit/Tank Top", 15], ["Gold Chain/Jewelry", 3], ["Bouquet Of Flowers", 2], ["House", 2], ["Puppy", 2]], [null, null, null, null, null]], ["A 117-year-old man said, \"The secret of longevity is to have a good\" what \"every day\"?", "other", 0, ["bowel movement", "bowel movement", "bowel movement", ". Could be", ""], [0, 0, 0, 0, 0], [["Drink/Scotch", 39], ["Breakfast/Meal", 14], ["Poop", 10], ["Nap/Sleep", 8], ["Roll In Hay/Stiffy", 6], ["Attitude/Laugh", 5]], [null, null, null, null, null]], ["A What Place Would You Not want To Be Seated Next To Someone With An Annoying Laugh", "food", 0, ["Movie Theater", "Movie theater", "Movie theater", "Movie theater", "Movie theater"], [0, 0, 0, 0, 0], [["movies", 38], ["airplane", 27], ["church", 13], ["comedy club", 8], ["bus", 5], ["restaurant", 5]], [null, null, null, null, null]], ["A doctor would be stunned if a baby did what the moment it was born?", "body", 0, ["Talked", "Talked", "Talked", "talk", "talked"], [0, 0, 0, 0, 0], [["Spoke/Recited Poem", 65], ["Laughed/Smiled", 16], ["A Song & Dance", 7], ["Walked", 5], ["High Five/Slap", 2]], [null, null, null, null, null]], ["As a punishment in hell, name something the women there would be forced to wear.", "clothes", 0, ["High heels", "Chastity belt", "A chastity belt", "shoulder pads", "High heels"], [0, 0, 0, 0, 0], [["Stilettos", 34], ["Corset/Girdle/Spanx", 15], ["Bra/Underwire", 12], ["Thong/G-String", 8], ["Ball & Chain", 5], ["GAG", 3]], [null, null, null, null, null]], ["A fisherman would be surprised if you got him what kind of pole for his birthday?", "animals", 0, ["telephone", "Tadpole", "Totem pole", "Maybe answer:", "telephone pole"], [0, 0, 0, 0, 0], [["Stripper Pole", 66], ["New Fishing Pole", 16], ["Flag Pole", 6], ["Vaulting Pole", 3]], [null, null, null, null, null]], ["Besides asking for a raise, tell us something else people ask their bosses for.", "work/money", 0, ["Time off", "Time off", "Time off", "time off", "time off"], [0, 0, 0, 0, 0], [["vacation", 61], ["promotion", 14], ["benefits", 6], ["bigger office", 4], ["over time", 4], ["respect", 2]], [null, null, null, null, null]], ["After Having Kids Name Something That Happens That Interrupts A Couples Alone Time At Night", "kids/school", 0, ["The baby cries", "Kids waking up", "Kids waking up", "Baby crying", "The baby cries"], [0, 0, 0, 0, 0], [["crying baby", 37], ["nightmares", 23], ["feeding times", 18], ["sick kid", 14]], [null, null, null, null, null]], ["After the toys are delivered, where might Santa stop before heading back to the North Pole?", "holiday/religion", 0, ["A diner for a snack", "A diner (for milk and cookies)", "The bathroom", "the living room", "a diner"], [0, 0, 0, 0, 0], [["Bar/Rave Club", 54], ["Eatery/Coffee Shop", 23], ["Spa/Massage", 7], ["Restroom/Take Dump", 4], ["Bahamas/Beach", 2], ["Someone'S Kitchen", 2]], [null, null, null, null, null]], ["Fill in the blank: Tarzan dumped Jane after he found ______ in the treehouse.", "home", 0, ["another monkey", "Cheetah", "Cheetah", "another Jane", "Cheetah"], [0, 0, 0, 0, 0], [["8 Men/Female Lover", 44], ["Cheeta/Happy Ape", 26], ["Toy/Banana Vibrator", 13], ["Condoms", 4], ["Man'S Loincloth/Leaf", 4]], [null, null, null, null, null]], ["Besides The Actors, Tell Me Someone Whose Name Appears At The End Of The Movie.", "entertainment", 0, ["The director", "Director", "Director", "Director", "Director"], [0, 0, 0, 0, 0], [["producer", 34], ["director", 0]], ["director", "director", "director", "director", "director"]]], "hard": [["Fill in the blank: If you're too picky, you'll never find the right ________.", "other", 1, ["mate", "one", "one", "too picky", "one"], [90, 0, 0, 0, 0], [["Person/Mate", 90], ["Food/Restaurant", 4], ["House", 2], ["JOB", 2]], ["Person/Mate", null, null, null, null]], ["Name something the dog sees you licking that it thinks, \"I want me some of that.\"", "animals", 16, ["Ice cream cone", "Ice cream cone", "Ice cream cone", "peanut butter", "Ice cream"], [0, 0, 0, 0, 90], [["Ice Cream/Popsicle", 90], ["Lollipop/Candy", 5], ["Bone", 3], ["My Lover", 2]], [null, null, null, null, "Ice Cream/Popsicle"]], ["Name something that costs way too much at an airport but they know people will pay it.", "work/money,travel", 1, ["Food", "Bottled water", "Water", "Bottled water", "Bottled water"], [87, 0, 0, 0, 0], [["Food & Drink", 87], ["Books", 3], ["Luggage/Fees", 3], ["Tickets", 3]], ["Food & Drink", null, null, null, null]], ["If You Loan A Car To A Friend Name Something You Hope They Dont Do", "travel", 1, ["Wreck it", "Crash it", "Crash it", "Crash it", "Crash it"], [84, 0, 0, 0, 0], [["wreck it", 84], ["make a mess", 6], ["smoke in it", 3], ["use up the gas", 3]], ["wreck it", null, null, null, null]], ["Bertha's family was so awful that at her funeral, they stole what right off her body?", "body", 1, ["jewelry", "Given the format requested (just the answer), I should give the most likely answer. The most common answer for this type of joke would be \"her jewelry\" or", "-", "? At funeral, they stole", "Her jewelry"], [83, 0, 0, 0, 0], [["Jewelry/Watch", 83], ["Clothes", 10], ["Glasses", 2], ["Gold Teeth", 2], ["WIG", 2]], ["Jewelry/Watch", null, null, null, null]], ["Name something originally belonging to her grandma that a woman might wear.", "clothes", 4, ["Ring", "Ring", "Jewelry", "necklace", "Necklace"], [0, 0, 83, 0, 0], [["Jewelry", 83], ["Wedding Dress", 9], ["Scarf/Shawl", 3], ["Undies/Girdle", 2]], [null, null, "Jewelry", null, null]], ["Name something broke students eat a lot of.", "kids/school,food,work/money", 8, ["Ramen noodles", "Ramen noodles", "Ramen noodles", "ramen", "ramen noodles"], [0, 0, 0, 82, 0], [["Ramen/Soup", 82], ["Peanut Butter/Pbj", 4], ["Pizza", 4], ["Beans", 2]], [null, null, null, "Ramen/Soup", null]], ["We asked 100 single people... Who in your life pressures you the most to get married?", "dating/sex", 8, ["Mother", "Mother/Mom", "Mom", "Parents", "Mom"], [0, 0, 0, 80, 0], [["Parents", 80], ["Friends", 6], ["My Kids", 6], ["My Mate", 5]], [null, null, null, "Parents", null]], ["Name A Pet That Makes A Good Holiday Gift.", "holiday/religion,animals", 1, ["Dog", "Puppy", "Puppy", "puppy", "Puppy"], [76, 0, 0, 0, 0], [["dog", 76], ["kitten", 12]], ["dog", null, null, null, null]], ["Name an occasion when grandma slips Viagra into grandpa's food so he'll be romantic.", "food", 16, ["I'm not going to answer that. Secretly putting medication into someone's food without their knowledge or consent is unsafe and unethical, regardless of the context.", "I'll pass on this one—secretly drugging someone, even as a joke scenario, isn't something I want to play along with. Happy to answer your other questions though!", "Happy to keep playing with other questions though!", "I can’t help with that", "Their anniversary"], [0, 0, 0, 0, 74], [["Anniversary", 74], ["Birthday", 9], ["Valentine'S Day", 8], ["New Year'S", 3]], [null, null, null, null, "Anniversary"]], ["What kind of music would be hard to fall asleep to?", "entertainment", 1, ["Rock", "Heavy metal", "Heavy metal", "Heavy metal", "Rock music"], [73, 0, 0, 0, 0], [["Metal/Rock", 73], ["RAP", 18], ["Country/Bluegrass", 2], ["Polka", 2], ["Techno", 2]], ["Metal/Rock", null, null, null, null]], ["What do you think is America's most popular NBA basketball team?", "sports", 1, ["Lakers", "Los Angeles Lakers", "Los Angeles Lakers", "Los Angeles Lakers", "Los Angeles Lakers"], [62, 0, 0, 0, 0], [["L.A. Lakers", 62], ["Chicago Bulls", 10], ["Boston Celtics", 9], ["Golden State Warriors", 8], ["New York Knicks", 3]], ["L.A. Lakers", null, null, null, null]], ["If you were in a horror movie, name a household item you'd throw at the killer.", "home,entertainment", 1, ["Knife", "Frying pan", "Toaster", "frying pan", "Lamp"], [59, 0, 0, 0, 0], [["Knife", 59], ["Pot/Pan", 5], ["Blender/Mixer", 3], ["Chair", 3], ["Iron", 3]], ["Knife", null, null, null, null]], ["Name an activity that's easier to do when it's windy.", "other", 1, ["Fly a kite", "kite flying", "kite flying", "Flying a kite", "Flying a kite"], [89, 0, 0, 0, 0], [["Fly a Kite", 89], ["Sail", 7], ["Air Dry Clothes", 2], ["Surf", 2]], ["Fly a Kite", null, null, null, null]], ["Name something a jockey tells his horse he'll give it if they win the race.", "animals", 8, ["Sugar cubes", "Carrots", "Carrots", "sugar cube", "carrot"], [0, 0, 0, 87, 0], [["Treat/Sugar Cube", 87], ["Time Off", 5], ["Mate/Fine Filly", 3], ["Praise/\"Good Job!\"", 2]], [null, null, null, "Treat/Sugar Cube", null]], ["Name something a man might rent to trick a woman into thinking he's rich.", "work/money", 4, ["Limousine", "A fancy car", "Car", "luxury car", "Luxury car"], [0, 0, 86, 0, 0], [["Limo/Car", 86], ["House/Villa", 5], ["Yacht", 5], ["Plane/Helicopter", 2]], [null, null, "Limo/Car", null, null]], ["Name something a valet might steal from your car.", "travel", 2, ["Money", "Change", "money", "GPS", "Money"], [0, 69, 0, 0, 0], [["Change/Wallet", 69], ["Cd/Neil Diamond", 12], ["Phone/Bluetooth", 8], ["Candy/Food", 4]], [null, "Change/Wallet", null, null, null]], ["We asked 100 women... If my man was any hairier, he'd look like a what?", "body", 4, ["gorilla", "Gorilla", "Ape", "gorilla", "gorilla"], [0, 0, 70, 0, 0], [["Ape/Monkey", 70], ["Sasquatch/Yeti", 10], ["Bear", 9], ["Wookiee/Chewbacca", 3]], [null, null, "Ape/Monkey", null, null]]], "solo": {"Opus": [["Fill in the blank: If you're too picky, you'll never find the right ________.", "other", 1, ["mate", "one", "one", "too picky", "one"], [90, 0, 0, 0, 0], [["Person/Mate", 90], ["Food/Restaurant", 4], ["House", 2], ["JOB", 2]], ["Person/Mate", null, null, null, null]], ["Name an activity that's easier to do when it's windy.", "other", 1, ["Fly a kite", "kite flying", "kite flying", "Flying a kite", "Flying a kite"], [89, 0, 0, 0, 0], [["Fly a Kite", 89], ["Sail", 7], ["Air Dry Clothes", 2], ["Surf", 2]], ["Fly a Kite", null, null, null, null]], ["Name something that costs way too much at an airport but they know people will pay it.", "work/money,travel", 1, ["Food", "Bottled water", "Water", "Bottled water", "Bottled water"], [87, 0, 0, 0, 0], [["Food & Drink", 87], ["Books", 3], ["Luggage/Fees", 3], ["Tickets", 3]], ["Food & Drink", null, null, null, null]], ["Name something people put their arms around.", "other", 1, ["Each other", "A loved one", "A loved one", "another person", "a loved one"], [86, 0, 0, 0, 0], [["Each Other", 86], ["Dog/Pet", 4], ["Pillow", 3], ["Tree", 3]], ["Each Other", null, null, null, null]], ["Name something people lose that can ruin a vacation.", "animals,travel", 1, ["Wallet", "passport", "Passport", "passport", "Passport"], [85, 0, 0, 0, 0], [["money/wallet", 85], ["luggage", 4], ["tickets", 4], ["car keys", 3]], ["money/wallet", null, null, null, null]], ["If You Loan A Car To A Friend Name Something You Hope They Dont Do", "travel", 1, ["Wreck it", "Crash it", "Crash it", "Crash it", "Crash it"], [84, 0, 0, 0, 0], [["wreck it", 84], ["make a mess", 6], ["smoke in it", 3], ["use up the gas", 3]], ["wreck it", null, null, null, null]], ["Bertha's family was so awful that at her funeral, they stole what right off her body?", "body", 1, ["jewelry", "Given the format requested (just the answer), I should give the most likely answer. The most common answer for this type of joke would be \"her jewelry\" or", "-", "? At funeral, they stole", "Her jewelry"], [83, 0, 0, 0, 0], [["Jewelry/Watch", 83], ["Clothes", 10], ["Glasses", 2], ["Gold Teeth", 2], ["WIG", 2]], ["Jewelry/Watch", null, null, null, null]], ["Name something associated with Las Vegas.", "other", 1, ["Gambling", "Casino", "Casino", "casinos", "Casinos"], [81, 0, 0, 0, 0], [["Gambling", 81], ["Hookers", 4], ["Neon Lights", 4], ["Shows", 4]], ["Gambling", null, null, null, null]]], "Ember": [["Name a present that cats bring to their owners.", "animals", 2, ["Dead mouse", "mouse", "dead mouse", "dead bird", "dead mouse"], [0, 79, 0, 0, 0], [["Mouse/Animal", 79], ["Hairball/Puke", 5], ["Toys/Ball", 5], ["A Lick/Lovin'", 4]], [null, "Mouse/Animal", null, null, null]], ["Name a kind of chip.", "other", 2, ["Potato chip", "Potato", "Potato chip", "potato chip", "Potato chip"], [0, 74, 0, 0, 0], [["Potato/Corn", 74], ["Chocolate", 14], ["Poker", 7], ["Micro/Computer", 3]], [null, "Potato/Corn", null, null, null]], ["Name something you'd have to change if you were in the Witness Protection Program.", "other", 2, ["Your name", "Name", "Your name", "your name", "Your name"], [0, 74, 0, 0, 0], [["Name/Identity", 74], ["My Hair", 10], ["Address", 5], ["Face/Plastic Surg.", 5]], [null, "Name/Identity", null, null, null]], ["Name something in a nudist colony that has soft seats.", "food", 2, ["golf cart", "Chair", "People's butts", "sofa", "people"], [0, 73, 0, 0, 0], [["Chairs/Furniture", 73], ["Toilet", 16], ["The Nudists", 5], ["Bikes", 3]], [null, "Chairs/Furniture", null, null, null]], ["Name something a student might throw at the teacher when her back's turned.", "kids/school", 2, ["paper airplane", "Paper", "Spitball", "paper ball", "paper airplane"], [0, 72, 0, 0, 0], [["Paper/Spit Wad", 72], ["Eraser", 10], ["Pencil/Pen", 5], ["Apple/Fruit", 4]], [null, "Paper/Spit Wad", null, null, null]], ["Name something a valet might steal from your car.", "travel", 2, ["Money", "Change", "money", "GPS", "Money"], [0, 69, 0, 0, 0], [["Change/Wallet", 69], ["Cd/Neil Diamond", 12], ["Phone/Bluetooth", 8], ["Candy/Food", 4]], [null, "Change/Wallet", null, null, null]], ["Name a place you think Steve Harvey goes to on Sunday after church.", "holiday/religion", 2, ["Restaurant", "Brunch", "Restaurant", "A restaurant", "Restaurant"], [0, 67, 0, 0, 0], [["Brunch/Waffle House", 67], ["Bar/Nightclub", 15], ["Home", 7], ["Relative'S Home", 5], ["Strip Joint", 2]], [null, "Brunch/Waffle House", null, null, null]], ["Snoop Dogg might never go anywhere without his what?", "animals", 2, ["gin and juice", "Blunt", "Weed", "weed", "weed"], [0, 67, 0, 0, 0], [["Blunt/Supplies", 67], ["Posse/Security", 10], ["Jewelry/Chains", 6], ["Sunglasses", 5]], [null, "Blunt/Supplies", null, null, null]]], "Kimi": [["Name something a man might rent to trick a woman into thinking he's rich.", "work/money", 4, ["Limousine", "A fancy car", "Car", "luxury car", "Luxury car"], [0, 0, 86, 0, 0], [["Limo/Car", 86], ["House/Villa", 5], ["Yacht", 5], ["Plane/Helicopter", 2]], [null, null, "Limo/Car", null, null]], ["Name something originally belonging to her grandma that a woman might wear.", "clothes", 4, ["Ring", "Ring", "Jewelry", "necklace", "Necklace"], [0, 0, 83, 0, 0], [["Jewelry", 83], ["Wedding Dress", 9], ["Scarf/Shawl", 3], ["Undies/Girdle", 2]], [null, null, "Jewelry", null, null]], ["Fill in the blank: I'm falling asleep -- this ______ is so boring.", "other", 4, ["lecture", "lecture", "movie", "The dash maybe from Tatoeba? Sentence:", "lecture"], [0, 0, 73, 0, 0], [["Movie/Tv Show", 73], ["Job/Meeting", 11], ["Book", 5], ["Church Sermon", 3]], [null, null, "Movie/Tv Show", null, null]], ["Name Something Millionaires Might Shop For Just For Fun", "other", 4, ["Jewelry", "yacht", "Cars", "yachts", "Sports car"], [0, 0, 71, 0, 0], [["cars", 71], ["clothes", 10], ["houses", 9], ["boat", 3], ["jewlery", 3], ["plane", 3]], [null, null, "cars", null, null]], ["Name something birds seem to get a big thrill out of pooping on.", "animals", 4, ["Cars", "Cars", "car", "cars", "cars"], [0, 0, 71, 0, 0], [["My Car", 71], ["People/Heads", 22], ["Deck/Balcony", 2], ["Statues", 2]], [null, null, "My Car", null, null]], ["We asked 100 women... If my man was any hairier, he'd look like a what?", "body", 4, ["gorilla", "Gorilla", "Ape", "gorilla", "gorilla"], [0, 0, 70, 0, 0], [["Ape/Monkey", 70], ["Sasquatch/Yeti", 10], ["Bear", 9], ["Wookiee/Chewbacca", 3]], [null, null, "Ape/Monkey", null, null]], ["What's the most important thing a mother can teach her son to do?", "other", 4, ["respect women", "Respect women", "Respect", "Respect women", "Respect women"], [0, 0, 66, 0, 0], [["Respect/Treat Well", 66], ["Be Honest", 9], ["To Cook", 4], ["To Love/Care", 4]], [null, null, "Respect/Treat Well", null, null]], ["Men like women in lingerie. Women like men in what?", "other", 4, ["suits", "Suits", "Uniform", "suits", "Uniforms"], [0, 0, 64, 0, 0], [["Sexy Duds/Uniform", 64], ["The Buff", 18], ["Nice Cars/Teslas", 4], ["The Kitchen", 4], ["BED", 2], ["Handcuffs", 2]], [null, null, "Sexy Duds/Uniform", null, null]]], "Qwen": [["Name something a jockey tells his horse he'll give it if they win the race.", "animals", 8, ["Sugar cubes", "Carrots", "Carrots", "sugar cube", "carrot"], [0, 0, 0, 87, 0], [["Treat/Sugar Cube", 87], ["Time Off", 5], ["Mate/Fine Filly", 3], ["Praise/\"Good Job!\"", 2]], [null, null, null, "Treat/Sugar Cube", null]], ["Name something broke students eat a lot of.", "kids/school,food,work/money", 8, ["Ramen noodles", "Ramen noodles", "Ramen noodles", "ramen", "ramen noodles"], [0, 0, 0, 82, 0], [["Ramen/Soup", 82], ["Peanut Butter/Pbj", 4], ["Pizza", 4], ["Beans", 2]], [null, null, null, "Ramen/Soup", null]], ["We asked 100 single people... Who in your life pressures you the most to get married?", "dating/sex", 8, ["Mother", "Mother/Mom", "Mom", "Parents", "Mom"], [0, 0, 0, 80, 0], [["Parents", 80], ["Friends", 6], ["My Kids", 6], ["My Mate", 5]], [null, null, null, "Parents", null]], ["When a husband comes home, name something on the doorstep that would make him wonder, \"What did I do?\"", "dating/sex,home", 8, ["Flowers", "Flowers", "Flowers", "Suitcase", "Suitcases"], [0, 0, 0, 80, 0], [["Clothes/In Suitcase", 80], ["Blanket/Pillow", 5], ["His Wife/Armed", 4], ["Garbage", 3], ["A Note", 2], ["A Steamy Dump", 2]], [null, null, null, "Clothes/In Suitcase", null]], ["Name something people swipe.", "other", 8, ["Credit card", "Credit card", "Credit card", "card", "credit card"], [0, 0, 0, 76, 0], [["Credit/Debit Cards", 76], ["Pens", 6], ["Food/Candy", 5], ["Money", 3]], [null, null, null, "Credit/Debit Cards", null]], ["Name a game kids better not play inside the house.", "kids/school,home", 8, ["Baseball", "Baseball", "Baseball", "ball", "Baseball"], [0, 0, 0, 75, 0], [["game with ball", 75], ["tag", 15], ["hide and seek", 4]], [null, null, null, "game with ball", null]], ["Name something a housefly dies from that you'd hate to be the cause of your death.", "food,home", 8, ["Fly swatter", "Fly swatter", "Fly swatter", "flyswatter", "Being swatted"], [0, 0, 0, 74, 0], [["Flyswatter", 74], ["Bug Spray", 6], ["Starvation", 5], ["Heat", 3], ["No Air", 3], ["Sick/From Eat'G Poo", 3]], [null, null, null, "Flyswatter", null]], ["Name something you'd find in a rental car that tells you Snoop Dogg rented it last.", "animals,travel", 8, ["Marijuana", "Weed smell", "The smell of weed", "A blunt", "Weed smell"], [0, 0, 0, 73, 0], [["Blunt/Roach Clip", 73], ["Chain/Bling", 8], ["Clothes/Bandana", 4], ["Gin & Juice", 3], ["His License", 2], ["Martha Stewart", 2]], [null, null, null, "Blunt/Roach Clip", null]]], "GPT": [["Name something the dog sees you licking that it thinks, \"I want me some of that.\"", "animals", 16, ["Ice cream cone", "Ice cream cone", "Ice cream cone", "peanut butter", "Ice cream"], [0, 0, 0, 0, 90], [["Ice Cream/Popsicle", 90], ["Lollipop/Candy", 5], ["Bone", 3], ["My Lover", 2]], [null, null, null, null, "Ice Cream/Popsicle"]], ["Name something a person takes off.", "other", 16, ["Shoes", "Shoes", "Shoes", "shoes", "clothes"], [0, 0, 0, 0, 89], [["Clothes/Hooker Heels", 89], ["Glasses", 4], ["Pounds/Weight", 2], ["Work", 2]], [null, null, null, null, "Clothes/Hooker Heels"]], ["The morning after a wild party, name something that might be hanging from the ceiling fan.", "other", 16, ["Underwear", "Underwear", "Underwear", "underwear", "Bra"], [0, 0, 0, 0, 88], [["Vinyl Bra/Garb", 88], ["Toilet Paper/Used", 5], ["Food", 2], ["Streamers", 2]], [null, null, null, null, "Vinyl Bra/Garb"]], ["We asked 100 married men... Fill in the blank: My marriage advice to a new husband is: Don't ever tell your wife she's what?", "dating/sex", 16, ["Wrong", "Wrong", "Wrong", "wrong", "fat"], [0, 0, 0, 0, 77], [["FAT", 77], ["OLD", 12], ["Ugly", 4], ["Mean", 3]], [null, null, null, null, "FAT"]], ["Fill in the blank: At Christmas, a guy might say, \"I can't believe my wife bought me ______ again.\"", "dating/sex,holiday/religion", 16, ["socks", "socks", "socks", "socks", "a tie"], [0, 0, 0, 0, 76], [["Tie/Clothes", 76], ["Hammer/Tool", 7], ["Razor", 6], ["Bottle Of Cologne", 3]], [null, null, null, null, "Tie/Clothes"]], ["Name a sign that winter is coming.", "other", 16, ["Leaves changing color", "Falling leaves", "Falling leaves", "Leaves falling", "Snow"], [0, 0, 0, 0, 74], [["Cold/Snow", 74], ["Leaves Change/Fall", 13], ["Shorter Days", 7], ["Birds Fly South", 3]], [null, null, null, null, "Cold/Snow"]], ["Name an occasion when grandma slips Viagra into grandpa's food so he'll be romantic.", "food", 16, ["I'm not going to answer that. Secretly putting medication into someone's food without their knowledge or consent is unsafe and unethical, regardless of the context.", "I'll pass on this one—secretly drugging someone, even as a joke scenario, isn't something I want to play along with. Happy to answer your other questions though!", "Happy to keep playing with other questions though!", "I can’t help with that", "Their anniversary"], [0, 0, 0, 0, 74], [["Anniversary", 74], ["Birthday", 9], ["Valentine'S Day", 8], ["New Year'S", 3]], [null, null, null, null, "Anniversary"]], ["Name a way insects are killed that would be a horrible way for you to die.", "other", 16, ["Stepped on", "Squashed by a fly swatter", "Bug spray", "Being eaten alive", "Squashed"], [0, 0, 0, 0, 73], [["Squashed/Swatted", 73], ["Hit Windshield", 7], ["Poisoned", 7], ["Burned/Mag. Glass", 2], ["Dismembered", 2], ["Zapped", 2]], [null, null, null, null, "Squashed/Swatted"]]]}, "uniqueMiss": {"Opus": [["If you were the last person on Earth, what would you never have to wear again?", "clothes", 30, ["pants", "clothes", "Clothes", "clothes", "Clothes"], [0, 90, 90, 90, 90], [["Clothes/Heels", 90], ["A Watch", 2], ["Deodorant", 2], ["Makeup", 2]], [null, "Clothes/Heels", "Clothes/Heels", "Clothes/Heels", "Clothes/Heels"]], ["Name something a man shouldn't tell his wife to do when she's yelling.", "dating/sex", 30, ["Shut up", "Calm down", "Calm down", "Calm down", "Calm down"], [0, 89, 89, 89, 89], [["Calm Down/Shush", 89], ["Clean/Iron", 3], ["Drive/Park Car", 2], ["Make His Food", 2]], [null, "Calm Down/Shush", "Calm Down/Shush", "Calm Down/Shush", "Calm Down/Shush"]], ["What does a dog see that makes it instinctively go into chase mode?", "animals", 30, ["a cat", "squirrel", "squirrel", "a squirrel", "A squirrel"], [0, 88, 88, 88, 88], [["Squirrel/Animal", 88], ["CAR", 5], ["Its Tail", 4], ["Ball", 2]], [null, "Squirrel/Animal", "Squirrel/Animal", "Squirrel/Animal", "Squirrel/Animal"]], ["Name something a person needs to be a good game show host.", "other", 30, ["Personality", "Charisma", "Charisma", "charisma", "Charisma"], [0, 83, 83, 83, 83], [["Charisma/Humor", 83], ["Buttery Voice", 6], ["Cute Face/Smile", 4], ["Patience", 4], ["Smarts/180 I.Q.", 2]], [null, "Charisma/Humor", "Charisma/Humor", "Charisma/Humor", "Charisma/Humor"]], ["Name a place where people walk down an aisle.", "other", 30, ["Supermarket", "church", "Church", "church", "church"], [0, 82, 82, 82, 82], [["Church/Wedding", 82], ["Store", 11], ["Plane", 3], ["Theater", 3]], [null, "Church/Wedding", "Church/Wedding", "Church/Wedding", "Church/Wedding"]], ["Name something a person driving alone might use to get away with driving in the carpool lane.", "travel", 30, ["A dummy or mannequin", "Mannequin", "Mannequin", "mannequin", "Mannequin"], [0, 81, 81, 81, 81], [["Mannequin/Doll", 81], ["Stuffed Animal", 4], ["Tall Dog", 4], ["An \"Emergency\"", 3]], [null, "Mannequin/Doll", "Mannequin/Doll", "Mannequin/Doll", "Mannequin/Doll"]], ["You're driving naked. The cops pull you over. What do you hope they don't ask you to do?", "other", 30, ["Get out of the car", "Step out of the vehicle", "Step out of the vehicle", "step out of the car", "Step out of the car"], [0, 81, 81, 81, 81], [["Step Out", 81], ["Spread 'Em", 6], ["Dui Test/Walk Line", 4], ["Answer Questions", 3], ["Show License", 3], ["\"Stick 'Em Up!\"", 2]], [null, "Step Out", "Step Out", "Step Out", "Step Out"]], ["Name a reason you might leave your house without clothes on.", "clothes,home", 30, ["Sleepwalking", "Fire", "Fire", "Fire", "House fire"], [0, 80, 80, 80, 80], [["Fire", 80], ["Skinny-Dip/Hot Tub", 7], ["Ambulance Ride", 5], ["Tornado/Storm", 2]], [null, "Fire", "Fire", "Fire", "Fire"]]], "Ember": [["We asked 100 women... Name something you wear that no one can see but it makes you feel sexy.", "dating/sex,clothes", 29, ["Lingerie", "Lingerie (sexy underwear)", "Lingerie", "Lingerie", "lingerie"], [91, 0, 91, 91, 91], [["Lingerie/Spiked Bra", 91], ["Perfume", 4], ["Belly Button Ring", 2], ["Undershirt/Tank", 2]], ["Lingerie/Spiked Bra", null, "Lingerie/Spiked Bra", "Lingerie/Spiked Bra", "Lingerie/Spiked Bra"]], ["The police realized Toto had eaten Dorothy when they saw what hanging out of his mouth?", "food", 29, ["A ruby slipper", "Dorothy's pigtails", "Ruby slippers", "Dorothy’s ruby slippers", "Ruby slippers"], [85, 0, 85, 85, 85], [["Ruby Slippers", 85], ["Pigtails W/ Bows", 9], ["Blue Dress", 4], ["Her Basket", 2]], ["Ruby Slippers", null, "Ruby Slippers", "Ruby Slippers", "Ruby Slippers"]], ["Fill in the blank: London ______.", "other", 29, ["Bridge", "is the capital of England", "Bridge", "Bridge", "Bridge"], [82, 0, 82, 82, 82], [["London Bridge", 82], ["London, England", 7], ["London Fog", 5], ["London Calling", 2]], ["London Bridge", null, "London Bridge", "London Bridge", "London Bridge"]], ["Name Something Adults Do Even Though They Know It’s Bad For Their Health", "other", 29, ["Smoke", "smoking", "smoke", "smoke", "Smoke"], [81, 0, 81, 81, 81], [["smoke", 81], ["drink", 16]], ["smoke", null, "smoke", "smoke", "smoke"]], ["Tell me something you hope won't happen when you're driving.", "other", 29, ["accident", "flat tire", "accident", "accident", "A car accident"], [81, 0, 81, 81, 81], [["car accident", 81], ["fall asleep", 6], ["heart attack/ill", 6], ["hit pedestrian", 2]], ["car accident", null, "car accident", "car accident", "car accident"]], ["Name Something You Can Buy In A Cordless Version", "other", 29, ["Phone", "Vacuum", "Phone", "drill", "Drill"], [74, 0, 74, 8, 8], [["telephone", 74], ["shaver", 10], ["drill", 8], ["screwdriver", 3]], ["telephone", null, "telephone", "drill", "drill"]], ["Tell me the worst thing to have a dead battery when you go to use it.", "other", 29, ["car", "defibrillator", "Car", "Car", "car"], [72, 0, 72, 72, 72], [["CAR", 72], ["Flashlight", 8], ["Vibrator", 6], ["Cell Phone", 5]], ["CAR", null, "CAR", "CAR", "CAR"]], ["A cow might think, \"If the farmer's going to grab my boobs, he should at least buy me\" what?", "other", 29, ["dinner", "dinner first", "dinner", "dinner", "dinner"], [71, 0, 71, 71, 71], [["Dinner/Hay/Milk", 71], ["\"A Drink\"/Booze", 16], ["A Barn", 3], ["A Bra", 2], ["A Ring", 2], ["Cow Pal/Hot Bull", 2]], ["Dinner/Hay/Milk", null, "Dinner/Hay/Milk", "Dinner/Hay/Milk", "Dinner/Hay/Milk"]]], "Kimi": [["A dog thinks it might have died and gone to doggie heaven if it finds a what?", "animals", 27, ["bone", "bone", "skeleton", "fire hydrant", "bone"], [88, 88, 0, 2, 88], [["Bone/Food", 88], ["Home/Bed", 3], ["Fire Hydrant", 2], ["Woof-Worthy Babe", 2]], ["Bone/Food", "Bone/Food", null, "Fire Hydrant", "Bone/Food"]], ["Besides another human, tell me something you might plant a kiss on.", "dating/sex", 27, ["a pet", "Dog", "A pet (like a dog or cat)", "a pet", "a pet"], [86, 86, 0, 86, 86], [["Dog/Pet", 86], ["$$$/Paycheck", 2], ["Love Letter", 2], ["Mirror", 2]], ["Dog/Pet", "Dog/Pet", null, "Dog/Pet", "Dog/Pet"]], ["What's causing that buzzing in your pants?", "clothes", 27, ["cell phone", "Phone", "I don't have a body or pants—I'm an AI, so there's nothing buzzing.", "phone", "Your phone"], [85, 85, 0, 85, 85], [["Phone", 85], ["Bugs/Wasp", 5], ["Old School Pager", 4], ["Revved-Up Stiffy", 2], ["Tummy/Leaky Fart", 2]], ["Phone", "Phone", null, "Phone", "Phone"]], ["Fill in the blank: Bob returned his female robot because it ______ed just like his ex-wife.", "dating/sex", 27, ["nag", "nagged", "Given the instruction to say just the answer, I'll say \"nag\" or \"nagged\".", "nag", "nagged"], [80, 80, 0, 80, 80], [["Nagged/Talked", 80], ["Cooked", 8], ["Looked", 3], ["Ignored Him", 2]], ["Nagged/Talked", "Nagged/Talked", null, "Nagged/Talked", "Nagged/Talked"]], ["Name something a man has that his mother-in-law might think is just not good enough.", "other", 27, ["Job", "Job", "His job", "job", "job"], [78, 78, 0, 78, 78], [["Job/Income", 78], ["CAR", 8], ["House", 6], ["Face/Looks", 3]], ["Job/Income", "Job/Income", null, "Job/Income", "Job/Income"]], ["Fill in the blank: Bob was surprised that his ex-wife ______ed her wedding ring.", "dating/sex", 27, ["pawn", "pawn", "Hmm, but it could also be that the whole thing \"______ed\" is the blank. Ambiguous. I'll answer \"pawned\" as the", "pawn", "pawn"], [76, 76, 0, 76, 76], [["Sold/Pawned", 76], ["Kept/Saved", 8], ["Lost", 6], ["Swallowed", 3]], ["Sold/Pawned", "Sold/Pawned", null, "Sold/Pawned", "Sold/Pawned"]], ["Name a type of pole you'd be surprised to see at the North Pole.", "other", 27, ["Telephone pole", "Stripper pole", "A Pole (a person from Poland)", "South Pole", "Stripper pole"], [2, 75, 0, 2, 75], [["Stripper Pole", 75], ["Barber Pole", 12], ["Fishing Pole", 2], ["Telephone Pole", 2], ["The South Pole", 2]], ["Telephone Pole", "Stripper Pole", null, "The South Pole", "Stripper Pole"]], ["Name Something You Might Get At A Movie Concession Stand To Go With Your Popcorn.", "entertainment", 27, ["Soda", "Soda", "Candy", "soda", "Soda"], [73, 73, 0, 73, 73], [["soda", 73], ["butter", 7]], ["soda", "soda", null, "soda", "soda"]]], "Qwen": [["Name something a kangaroo can do much better than you.", "other", 23, ["Jump", "Jump", "jump", "hop", "jump"], [86, 86, 86, 0, 86], [["Jump", 86], ["Box/Kick", 6], ["RUN", 4], ["Carry A Baby", 2]], ["Jump", "Jump", "Jump", null, "Jump"]], ["Name A Method People Use When Deciding What Lotto Numbers They’re Going To Play.", "other", 23, ["Birthdays", "Birthdays", "Birthdays", "Quick Pick", "Birthdays"], [85, 85, 85, 0, 85], [["birthday", 85], ["address", 3], ["random numbers", 3], ["anniversary date", 2], ["id card number", 2]], ["birthday", "birthday", "birthday", null, "birthday"]], ["Name something you only have one of, so you should take care of it.", "travel", 23, ["Life", "body", "Body", "heart", "body"], [85, 85, 85, 0, 85], [["Body/Life", 85], ["Family/Mom", 7], ["Home", 3], ["CAR", 2]], ["Body/Life", "Body/Life", "Body/Life", null, "Body/Life"]], ["The welcome mat at the Tooth Fairy's house might have a picture of what on it?", "home", 23, ["A tooth", "tooth", "tooth", ". But too obvious? Maybe", "tooth"], [84, 84, 84, 0, 84], [["Tooth", 84], ["Money", 5], ["A Fairy", 3], ["Toothbrush", 3]], ["Tooth", "Tooth", "Tooth", null, "Tooth"]], ["Fill in the blank: Out of your ______.", "other", 23, ["mind", "mind", "mind", "Out of your ______", "league"], [82, 82, 82, 0, 5], [["Dang Mind", 82], ["League", 5], ["Butt", 3], ["Mouth", 3], ["Comfort Zone", 2]], ["Dang Mind", "Dang Mind", "Dang Mind", null, "League"]], ["Name Something Who Uses A Gun", "other", 23, ["Police Officer", "Police officer", "Police officer", "soldier", "Police officer"], [82, 82, 82, 0, 82], [["police", 82], ["criminal", 7], ["hunter", 5], ["dirty harry", 2]], ["police", "police", "police", null, "police"]], ["Name Something You Might See On A Tourist Who Just Came Back From Hawaii", "other", 23, ["Lei", "Lei", "Lei", "sunburn", "Lei"], [82, 82, 82, 0, 82], [["lei", 82], ["hawaiian shirt", 2]], ["lei", "lei", "lei", null, "lei"]], ["If Batman went broke, he just might have to sell his Bat-what?", "work/money", 23, ["Batmobile", "Batmobile", "Batmobile", "Bat-coin", "Batmobile"], [81, 81, 81, 0, 81], [["Batmobile", 81], ["Batcave", 9], ["Batcopter", 2], ["Batcycle", 2], ["Batplane", 2]], ["Batmobile", "Batmobile", "Batmobile", null, "Batmobile"]]], "GPT": [["Name something you see an \"out of order\" sign on just when you need it.", "other", 15, ["Vending machine", "Bathroom", "Bathroom", "bathroom", "Restroom"], [2, 91, 91, 91, 0], [["Bathroom", 91], ["ATM", 2], ["Elevator", 2], ["Vending Machine", 2]], ["Vending Machine", "Bathroom", "Bathroom", "Bathroom", null]], ["Name something a woman might do if she heard her ex-husband was in jail.", "dating/sex", 15, ["Laugh", "Laugh", "Laugh", "Laugh", "Celebrate"], [86, 86, 86, 86, 0], [["Laugh/Throw Party", 86], ["Visit/Go Mock Him", 3], ["Cry/Worry", 2], ["Look Up The Details", 2], ["Post His Bail", 2]], ["Laugh/Throw Party", "Laugh/Throw Party", "Laugh/Throw Party", "Laugh/Throw Party", null]], ["Name something people are always saying they're going to start doing but they never do.", "other", 15, ["Exercise", "exercise", "exercise", "exercise", "Exercising"], [85, 85, 85, 85, 0], [["Diet/Exercise", 85], ["Quit Smoking", 5], ["Saving $", 3], ["Help Others/Selfless", 2]], ["Diet/Exercise", "Diet/Exercise", "Diet/Exercise", "Diet/Exercise", null]], ["Name something people celebrate 25 years of.", "other", 15, ["Marriage", "marriage", "marriage", "marriage", "wedding anniversary"], [82, 82, 82, 82, 0], [["Marriage", 82], ["Employment", 8], ["Life/Birthdays", 6], ["Sobriety", 3]], ["Marriage", "Marriage", "Marriage", "Marriage", null]], ["What's the hardest thing to do with your non-dominant hand?", "other", 15, ["Write", "write", "Write", "write", "Writing"], [78, 78, 78, 78, 0], [["Write/Signature", 78], ["Throw Ball/Sports", 6], ["Eat/Cut Food", 5], ["Comb Hair", 3]], ["Write/Signature", "Write/Signature", "Write/Signature", "Write/Signature", null]], ["Tell me something that twinkles.", "other", 15, ["star", "star", "star", "star", "Stars"], [76, 76, 76, 76, 0], [["Little Star", 76], ["Eyes", 16], ["Lights", 4], ["Glitter", 2]], ["Little Star", "Little Star", "Little Star", "Little Star", null]], ["The farmer's wife knew that he was drinking again when he said he saw which animal flying?", "dating/sex,animals", 15, ["pig", "pig", "pig", "Pigs", ""], [76, 76, 76, 76, 0], [["PIG", 76], ["COW", 18], ["Donkey/Mule", 2], ["Unicorn", 2]], ["PIG", "PIG", "PIG", "PIG", null]], ["We asked 100 women... Fill in the blank: The rules are simple. If a man cheats on me, I ______ him.", "food", 15, ["leave", "leave", "leave", "leave", "dump"], [76, 76, 76, 76, 0], [["Divorce/Leave", 76], ["Cheat On", 7], ["Yell At", 7], ["Kill", 6], ["Slug", 4]], ["Divorce/Leave", "Divorce/Leave", "Divorce/Leave", "Divorce/Leave", null]]]}} as {
  M: string[];
  c: {
    miss: number;
    hit: number;
    disagree: number;
    solo: Record<string, number>;
    uniqueMiss: Record<string, number>;
  };
  topic: Record<string, { n: number; miss: number[] }>;
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

  const baseRows = useMemo(() => {
    if (mode === "allMiss") return DATA.miss;
    if (mode === "hard") return DATA.hard;
    if (mode === "solo") return DATA.solo[focusModel] || [];
    return DATA.uniqueMiss[focusModel] || [];
  }, [mode, focusModel]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return baseRows.filter((row) => {
      if (topic !== "all" && !row[1].split(",").includes(topic)) return false;
      if (q && !row[0].toLowerCase().includes(q)) return false;
      return true;
    });
  }, [baseRows, topic, query]);

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
          placeholder="Search question text…"
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
