"""
Production-Ready Menu Extractor for Raj Juice Co.
Extracts menu items from PDF with smart categorization and cleaning
"""

import os
import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict, field
import pdfplumber


@dataclass
class MenuItem:
    """Menu item data structure"""
    id: int
    name: str
    price: float
    category: str
    sub_category: str = ""
    is_vegetarian: bool = True
    is_chef_special: bool = False
    tags: List[str] = field(default_factory=list)


class MenuExtractor:
    """Advanced menu extractor"""
    
    def __init__(self):
        # Category keywords for smart detection
        self.categories = {
            'Main Course': [
                'dal', 'rajma', 'chole', 'palak', 'aloo', 'gobhi',
                'mushroom', 'paneer', 'khoya', 'matar', 'corn', 'veg',
                'soya', 'chaap', 'kofta', 'malai', 'curry', 'masala', 'bhuna'
            ],
            'Tandoor': [
                'tikka', 'tandoor', 'tandoori', 'afghani', 'achari',
                'haryali', 'malai tikka', 'kabab', 'sholey'
            ],
            'Breads': [
                'roti', 'naan', 'paratha', 'prantha', 'bread',
                'rumali', 'laccha', 'missi', 'chur chur'
            ],
            'Rice': [
                'rice', 'biryani', 'pulav', 'pulaw'
            ],
            'Desserts': [
                'waffle', 'brownie', 'sundae', 'gulab', 'jamun',
                'ice cream', 'chocolate'
            ],
            'Momos': [
                'momos', 'momo'
            ],
            'Thalis': [
                'thali', 'meal'
            ],
            'Combos': [
                'combo', 'sandwich', 'burger', 'with rice', 'with noodles', 'with fried rice'
            ],
            'Beverages': [
                'coffee', 'juice', 'shake', 'water', 'drink', 'soda', 'tea'
            ],
            'Add-ons': [
                'raita', 'salad', 'chutney', 'extra', 'gulab jamun single'
            ]
        }
        
        # OCR corrections
        self.corrections = {
            'Pancer': 'Paneer', 'Faneer': 'Paneer', 'Banarsi': 'Banarasi',
            'Babycorm': 'Baby Corn', 'Makhanwala': 'Makhani',
            'Lasooni': 'Lasuni', 'Adriki': 'Adraki', 'Kurchen': 'Kadhai',
            'Manchuriyan': 'Manchurian', 'Briyani': 'Biryani',
            'Haidrabadi': 'Hyderabadi', 'lce': 'Ice', 'ltem': 'Item',
            'Delexe': 'Deluxe', 'Pecs': 'Pcs', 'Nutela': 'Nutella',
            'Kit Kit': 'Kit Kat', 'Carmel': 'Caramel', 'Strewberry': 'Strawberry',
            'Banarna': 'Banana', 'Chur Chur.': 'Chur Chur', 'Spice Kholapuri': 'Kolhapuri',
            'Lazeej': 'Lazeez', 'Lababdar': 'Lababdaar', 'Makhanwali': 'Makhani',
            'ulab': 'Gulab'
        }
        
        # Patterns to exclude
        self.exclude_patterns = [
            r'@gmail', r'\d{10}', r'Follow', r'Contact:', r'Franchise',
            r'Est\. 1990', r'Delivery', r'www\.', r'Mob\.:', r'DELHI',
            r'NOIDA', r'About Us', r'Trust', r'Juices.*Shakes',
            r'ALL ABOVE', r'SERVE WITH', r'ON MRP', r'fssaí', r'GAUR CITY',
            r'ICE CREAM & More', r'You Can', r'Name', r'Only$'
        ]

    def extract(self, pdf_path: str) -> List[MenuItem]:
        """Main extraction pipeline"""
        
        print("\n" + "="*70)
        print("🍽️  MENU EXTRACTOR - RAJ JUICE CO.")
        print("="*70 + "\n")
        
        items = []
        
        # Extract items
        print("📖 Extracting menu items...")
        text_items = self._extract_from_text(pdf_path)
        items.extend(text_items)
        print(f"   Found: {len(text_items)} raw items")
        
        # Clean and validate
        print("\n🧹 Cleaning and validating...")
        cleaned_items = []
        for item in items:
            if self._is_valid(item):
                cleaned = self._clean(item)
                if cleaned:
                    cleaned_items.append(cleaned)
        
        print(f"   Validated: {len(cleaned_items)} items")
        
        # Deduplicate
        unique_items = self._deduplicate(cleaned_items)
        print(f"   Unique: {len(unique_items)} items")
        
        # Create final MenuItem objects
        final_items = []
        for idx, item in enumerate(sorted(unique_items, key=lambda x: (x['category'], x['name'])), 1):
            final_items.append(MenuItem(
                id=idx,
                name=item['name'],
                price=item['price'],
                category=item['category'],
                sub_category=item.get('sub_category', ''),
                is_vegetarian=True,
                is_chef_special=item.get('is_chef_special', False),
                tags=item.get('tags', [])
            ))
        
        print(f"\n✅ Total: {len(final_items)} menu items extracted!\n")
        print("="*70 + "\n")
        
        return final_items

    def _extract_from_text(self, pdf_path: str) -> List[Dict]:
        """Extract using pattern matching"""
        items = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Pattern: "Item Name Price"
                # Matches: "Dal Fry 250", "Paneer Tikka Masala 280"
                pattern = r'([A-Z][a-z]+(?:\s+[A-Za-z()]+){1,4})\s+(\d{2,3})(?=\s|$|\n)'
                
                matches = re.finditer(pattern, text)
                for match in matches:
                    name = match.group(1).strip()
                    try:
                        price = float(match.group(2))
                        if 10 <= price <= 500:
                            # Get context for category
                            start = max(0, match.start() - 200)
                            context = text[start:match.start()]
                            category = self._detect_category(name, context)
                            
                            items.append({
                                'name': name,
                                'price': price,
                                'category': category
                            })
                    except:
                        continue
        
        return items

    def _detect_category(self, name: str, context: str = "") -> str:
        """Smart category detection with name priority"""
        name_lower = name.lower()
        
        # Priority 1: Check name for specific category indicators
        # Breads
        if any(word in name_lower for word in ['naan', 'roti', 'paratha', 'bread', 'chur chur']):
            return "Breads"
        
        # Desserts
        if any(word in name_lower for word in ['waffle', 'brownie', 'sundae', 'chocolate waffle', 'ice cream']):
            return "Desserts"
        
        # Tandoor
        if any(word in name_lower for word in ['tikka', 'tandoor', 'tandoori', 'afghani', 'achari', 'haryali', 'kabab']):
            return "Tandoor"
        
        # Momos
        if 'momos' in name_lower or 'momo' in name_lower:
            return "Momos"
        
        # Thalis
        if 'thali' in name_lower:
            return "Thalis"
        
        # Rice dishes (including biryani)
        if any(word in name_lower for word in ['biryani', 'pulav', 'rice']) and 'with rice' not in name_lower:
            return "Rice"
        
        # Combos (must check after rice to avoid biryani being classified as combo)
        if any(phrase in name_lower for phrase in ['with rice', 'with noodles', 'with fried rice', 'combo', 'meal']):
            return "Combos"
        
        # Beverages
        if any(word in name_lower for word in ['coffee', 'tea', 'juice', 'shake', 'water', 'drink']):
            return "Beverages"
        
        # Add-ons / Extras (but not biryani)
        if any(word in name_lower for word in ['raita', 'chutney', 'salad', 'gulab jamun']) and 'biryani' not in name_lower:
            return "Add-ons"
        
        # Priority 2: Main Course (default for dals, paneer, vegetables, etc.)
        return "Main Course"

    def _is_valid(self, item: Dict) -> bool:
        """Validate item"""
        name = item.get('name', '')
        price = item.get('price', 0)
        
        # Basic checks
        if len(name) < 4 or len(name) > 60:
            return False
        
        if not (10 <= price <= 500):
            return False
        
        # Exclude patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, name, re.IGNORECASE):
                return False
        
        # Must start with capital
        if not name[0].isupper():
            return False
        
        # Too many single letters = junk
        words = name.split()
        if len(words) > 2:
            single_letters = sum(1 for w in words if len(w) == 1)
            if single_letters > 1:
                return False
        
        # Must have food words
        food_words = [
            'dal', 'paneer', 'aloo', 'naan', 'roti', 'tikka', 'masala',
            'chaap', 'mushroom', 'rice', 'waffle', 'brownie', 'sundae',
            'thali', 'raita', 'palak', 'rajma', 'chole', 'gobhi', 'matar',
            'butter', 'kadhai', 'tandoor', 'paratha', 'biryani', 'pulav',
            'momos', 'malai', 'curry', 'fry', 'kofta', 'corn', 'soya',
            'khoya', 'coffee', 'juice', 'gulab', 'jamun', 'cream', 'makkhan',
            'makhan', 'hara', 'pyaz', 'onion', 'garlic', 'stuff', 'plain'
        ]
        
        name_lower = name.lower()
        if not any(word in name_lower for word in food_words):
            return False
        
        return True

    def _clean(self, item: Dict) -> Optional[Dict]:
        """Clean and enrich item"""
        name = item['name']
        
        # Apply OCR corrections
        for wrong, correct in self.corrections.items():
            # Case-insensitive replacement at word boundaries
            pattern = re.compile(rf'\b{re.escape(wrong)}\b', re.IGNORECASE)
            name = pattern.sub(correct, name)
        
        # Fix spacing
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Remove prefixes (only standalone letters followed by space, not part of words)
        name = re.sub(r'^[RVGErgve\-•*√✓]\s+', '', name)  # Changed + to \s+ so it requires space after
        
        # Ensure first letter is capitalized
        if name:
            name = name[0].upper() + name[1:] if len(name) > 1 else name.upper()
        
        # Chef special
        is_chef_special = bool(re.search(r'\([Cc]hef\s+[Ss]pecial', name))
        name = re.sub(r'\s*\([Cc]hef\s+[Ss]pecial[s]?\)', '', name)
        
        # Final cleanup
        name = name.strip()
        if not name or len(name) < 4:
            return None
        
        return {
            'name': name,
            'price': item['price'],
            'category': item['category'],
            'sub_category': self._detect_sub_category(name),
            'is_chef_special': is_chef_special,
            'tags': self._generate_tags(name, item['category'])
        }

    def _detect_sub_category(self, name: str) -> str:
        """Detect sub-category"""
        name_lower = name.lower()
        
        sub_cats = {
            'dal': 'Dals', 'paneer': 'Paneer', 'aloo': 'Potato',
            'mushroom': 'Mushroom', 'chaap': 'Soya Chaap',
            'tikka': 'Tikka', 'naan': 'Naans', 'roti': 'Rotis',
            'paratha': 'Parathas', 'rice': 'Rice', 'waffle': 'Waffles',
            'sundae': 'Sundaes', 'brownie': 'Brownies',
            'momos': 'Momos', 'thali': 'Thalis'
        }
        
        for keyword, sub_cat in sub_cats.items():
            if keyword in name_lower:
                return sub_cat
        
        return ""

    def _generate_tags(self, name: str, category: str) -> List[str]:
        """Generate tags"""
        tags = [category.lower().replace(' ', '-')]
        name_lower = name.lower()
        
        # Ingredients
        ingredients = [
            'paneer', 'dal', 'aloo', 'mushroom', 'corn', 'matar',
            'palak', 'chaap', 'rajma', 'chole', 'gobhi'
        ]
        tags.extend([ing for ing in ingredients if ing in name_lower])
        
        # Styles
        if any(w in name_lower for w in ['tandoor', 'tikka']):
            tags.append('tandoori')
        if 'fried' in name_lower:
            tags.append('fried')
        if any(w in name_lower for w in ['butter', 'malai', 'cream']):
            tags.append('creamy')
        if 'masala' in name_lower:
            tags.append('spicy')
        
        return list(set(tags))

    def _deduplicate(self, items: List[Dict]) -> List[Dict]:
        """Remove duplicates"""
        seen = set()
        unique = []
        
        for item in items:
            key = (item['name'].lower().strip(), item['price'])
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique

    def save_json(self, items: List[MenuItem], output_path: str):
        """Save to JSON"""
        try:
            data = [asdict(item) for item in items]
            
            # Ensure directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved: {output_path}\n")
        except PermissionError:
            print(f"❌ Permission denied: Cannot write to {output_path}")
            print("   Try saving to a different location or run with administrator privileges.")
            # Try current directory as fallback
            fallback_path = os.path.join(os.getcwd(), 'menu_structured_clean.json')
            try:
                with open(fallback_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Saved to fallback location: {fallback_path}\n")
            except Exception as e:
                print(f"❌ Could not save file: {e}\n")
                raise
        except Exception as e:
            print(f"❌ Error saving file: {e}\n")
            raise

    def print_summary(self, items: List[MenuItem]):
        """Print summary"""
        print("="*70)
        print("📊 SUMMARY")
        print("="*70 + "\n")
        
        print(f"Total Items: {len(items)}\n")
        
        # Categories
        cats = {}
        for item in items:
            cats[item.category] = cats.get(item.category, 0) + 1
        
        print("Categories:")
        for cat, count in sorted(cats.items()):
            print(f"  • {cat}: {count}")
        
        # Price
        prices = [item.price for item in items]
        print(f"\nPrice Range: ₹{min(prices):.0f} - ₹{max(prices):.0f}")
        print(f"Average: ₹{sum(prices)/len(prices):.0f}\n")
        
        # Sample
        print("Sample Items:")
        for item in items[:12]:
            special = "⭐" if item.is_chef_special else "  "
            print(f"  {special} {item.name:40s} ₹{item.price:>5.0f}  [{item.category}]")
        
        if len(items) > 12:
            print(f"  ... and {len(items) - 12} more\n")
        
        print("="*70 + "\n")


def main():
    """Main function"""
    import sys
    
    # Find PDF
    pdf_path = None
    
    # Check command line arguments first
    for arg in sys.argv[1:]:
        if arg.endswith('.pdf') and os.path.exists(arg):
            pdf_path = arg
            break
    
    # If not found, try default locations
    if not pdf_path:
        default_paths = [
            '/mnt/user-data/uploads/menu.pdf',  # For Claude environment
            'menu.pdf',                         # Current directory
            './menu.pdf',                       # Current directory explicit
            '../menu.pdf',                      # Parent directory
        ]
        for path in default_paths:
            if os.path.exists(path):
                pdf_path = path
                break
    
    if not pdf_path:
        print("❌ No PDF found!")
        print("\nUsage:")
        print("  python menu_extractor.py <menu.pdf>")
        print("\nExamples:")
        print("  python menu_extractor.py menu.pdf")
        print("  python menu_extractor.py /path/to/menu.pdf")
        print("\nOr place 'menu.pdf' in the current directory.")
        print("\nCurrent directory:", os.getcwd())
        return
    
    print(f"📄 Input: {pdf_path}\n")
    
    # Extract
    extractor = MenuExtractor()
    items = extractor.extract(pdf_path)
    
    if not items:
        print("⚠️  No items extracted!")
        return
    
    # Determine output path
    if '/mnt/user-data/uploads/' in pdf_path:
        # Claude environment - save to outputs
        output_path = '/mnt/user-data/outputs/menu_structured_clean.json'
    else:
        # Local environment - save next to the PDF
        pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
        if not pdf_dir:
            pdf_dir = os.getcwd()
        output_path = os.path.join(pdf_dir, 'menu_structured_clean.json')
    
    # Save
    extractor.save_json(items, output_path)
    
    # Summary
    extractor.print_summary(items)
    
    print("✅ Done!\n")


# if __name__ == "__main__":
#     main()