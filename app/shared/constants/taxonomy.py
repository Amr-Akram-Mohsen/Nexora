TAXONOMY = {
  "sections": [
    {
      "name": "News",
      "description": "Latest updates and announcements."
    },
    {
      "name": "Reviews",
      "description": "Hands-on product testing and expert opinions."
    },
    {
      "name": "Tutorials",
      "description": "Guides, tips, and how-to articles."
    },
    {
      "name": "Trends",
      "description": "Market insights and hot upcoming products."
    },
    {
      "name": "Community",
      "description": "Discussions and feedback from the community."
    }
  ],
  "categories": [
    {
      "name": "Electronics",
      "is_leaf": False,
      "children": [
        {
          "name": "Smartphones",
          "is_leaf": True,
          "search_keywords": ["mobile phones", "cell phones", "android", "iphone"]
        },
        {
          "name": "Laptops",
          "is_leaf": True,
          "search_keywords": ["notebooks", "ultrabooks", "macbook", "gaming laptops"]
        },
        {
          "name": "Tablets",
          "is_leaf": True,
          "search_keywords": ["ipad", "android tablets", "surface"]
        },
        {
          "name": "Smartwatches",
          "is_leaf": True,
          "search_keywords": ["apple watch", "galaxy watch", "fitness trackers"]
        },
        {
          "name": "Earbuds",
          "is_leaf": True,
          "search_keywords": ["true wireless", "airpods", "galaxy buds", "tws"]
        },
        {
          "name": "Headphones",
          "is_leaf": True,
          "search_keywords": ["over-ear", "noise cancelling headphones", "hi-fi audio"]
        },
        {
          "name": "Cameras",
          "is_leaf": True,
          "search_keywords": ["dslr", "mirrorless", "photography gear", "vlogging cameras"]
        }
      ]
    },
    {
      "name": "Perfumes",
      "is_leaf": False,
      "children": [
        {
          "name": "Niche & Artisanal",
          "is_leaf": True,
          "search_keywords": ["niche fragrance", "artisan perfume", "luxury scent"]
        },
        {
          "name": "Oud & Oriental",
          "is_leaf": True,
          "search_keywords": ["oud perfume", "arabic fragrance", "oriental scent", "attar"]
        }
      ]
    },
    {
      "name": "Accessories",
      "is_leaf": False,
      "children": [
        {
          "name": "Watches",
          "is_leaf": True,
          "search_keywords": ["luxury watches", "timepieces", "chronograph", "mechanical watches"]
        },
        {
          "name": "Bags",
          "is_leaf": True,
          "search_keywords": ["handbags", "backpacks", "luxury bags", "leather bags"]
        },
        {
          "name": "Sunglasses",
          "is_leaf": True,
          "search_keywords": ["luxury eyewear", "designer sunglasses", "shades"]
        },
        {
          "name": "Jewelry",
          "is_leaf": True,
          "search_keywords": ["fine jewelry", "rings", "necklaces", "bracelets"]
        }
      ]
    },
    {
      "name": "Uncategorized",
      "is_leaf": True
    }
  ],
  "topics": [
    {
      "name": "Gaming"
    },
    {
      "name": "Home Office"
    },
    {
      "name": "Photography"
    },
    {
      "name": "Fitness"
    },
    {
      "name": "Travel Gear"
    }
  ],
  "brands": [
    {
      "name": "Apple",
      "aliases": ["iphone", "macbook", "ipad", "airpods", "imac", "apple watch"]
    },
    {
      "name": "Samsung",
      "aliases": ["galaxy", "s24", "s23", "z fold", "z flip", "qled", "crystal uhd"]
    },
    {
      "name": "Sony",
      "aliases": ["playstation", "ps5", "bravia", "wh-1000xm", "wf-1000xm", "alpha"]
    },
    {
      "name": "Google",
      "aliases": ["pixel", "chromecast", "nest"]
    },
    {
      "name": "Microsoft",
      "aliases": ["surface", "xbox", "windows"]
    },
    {
      "name": "Dell",
      "aliases": ["xps", "alienware", "latitude", "inspiron"]
    },
    {
      "name": "HP",
      "aliases": ["spectre", "envy", "pavilion", "omen"]
    },
    {
      "name": "Lenovo",
      "aliases": ["thinkpad", "yoga", "legion"]
    },
    {
      "name": "Asus",
      "aliases": ["rog", "zenbook", "vivobook"]
    },
    {
      "name": "Nike",
      "aliases": ["air max", "jordan", "dunk"]
    },
    {
      "name": "Adidas",
      "aliases": ["yeezy", "ultraboost", "originals"]
    },
    {
      "name": "Rolex",
      "aliases": ["submariner", "daytona", "datejust"]
    },
    {
      "name": "Omega",
      "aliases": ["seamaster", "speedmaster"]
    },
    {
      "name": "Dior",
      "aliases": ["sauvage", "fahrenheit"]
    },
    {
      "name": "Chanel",
      "aliases": ["no. 5", "bleu de chanel", "chance"]
    }
  ],
  "facets": {
    "gender": [
      {
        "name": "Men"
      },
      {
        "name": "Women"
      },
      {
        "name": "Unisex"
      }
    ],
    "intent": [
      {
        "name": "Buying Guide"
      },
      {
        "name": "Gift Ideas"
      },
      {
        "name": "Comparison"
      },
      {
        "name": "Top List"
      },
      {
        "name": "Unboxing"
      },
      {
        "name": "First Impressions"
      },
      {
        "name": "Review"
      },
      {
        "name": "News"
      },
      {
        "name": "Tutorial"
      }
    ],
    "price_tier": [
      {
        "name": "Budget"
      },
      {
        "name": "Mid-Range"
      },
      {
        "name": "Premium"
      },
      {
        "name": "Luxury"
      }
    ],
    "attributes": [
      {
        "name": "Long-Lasting",
        "category": "Perfumes"
      },
      {
        "name": "Summer-Wear",
        "category": "Perfumes"
      },
      {
        "name": "Winter-Wear",
        "category": "Perfumes"
      },
      {
        "name": "Woody",
        "category": "Perfumes"
      },
      {
        "name": "Floral",
        "category": "Perfumes"
      },
      {
        "name": "Citrus",
        "category": "Perfumes"
      },
      {
        "name": "Spicy",
        "category": "Perfumes"
      },
      {
        "name": "Musky",
        "category": "Perfumes"
      },
      {
        "name": "Fresh",
        "category": "Perfumes"
      },
      {
        "name": "Sweet",
        "category": "Perfumes"
      },
      {
        "name": "Portable",
        "category": "Electronics"
      },
      {
        "name": "High Performance",
        "category": "Electronics"
      },
      {
        "name": "Lightweight",
        "category": "Electronics"
      },
      {
        "name": "Waterproof",
        "category": "Electronics"
      },
      {
        "name": "Noise Cancelling",
        "category": "Electronics"
      },
      {
        "name": "Battery Life",
        "category": "Electronics"
      },
      {
        "name": "Fast Charging",
        "category": "Electronics"
      },
      {
        "name": "Wireless",
        "category": "Electronics"
      }
    ]
  }
}
REDDIT_SUBREDDITS = {
    "community": {
        "electronics": ["gadgets", "smartphones", "Android", "iphone", "hardware", "Apple", "Samsung", "PCMasterRace", "GooglePixel"],
        "perfumes":    ["fragrance", "scents", "malefragrance", "feminineFragrance", "oud", "IndieExchange"],
        "accessories": ["Watches", "LuxuryPurse", "DesignerBags", "Sunglasses", "streetwear", "malefashionadvice"],
        "regional":    ["saudiarabia", "dubai", "abudhabi", "emirates"], 
    },
    "trends": {
        "electronics": ["technology", "futurology", "startups"],
        "perfumes":    ["fragrance", "scents"],
        "accessories": ["streetwear", "highfashion"],
    }
}
