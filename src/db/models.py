from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    language_code = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recipes = relationship("Recipe", back_populates="user")
    # images = relationship("RecipeImage", back_populates="user")  # if we want user images

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    cooking_time = Column(Integer, nullable=False)  # minutes
    difficulty = Column(String, nullable=False)
    servings = Column(Integer, nullable=False)
    cuisine = Column(String, nullable=False)
    chef_tip = Column(Text, nullable=True)
    serving_suggestion = Column(Text, nullable=True)
    image_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recipes")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    steps = relationship("RecipeStep", back_populates="recipe", cascade="all, delete-orphan")
    images = relationship("RecipeImage", back_populates="recipe", cascade="all, delete-orphan")

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    name = Column(String, nullable=False)
    quantity = Column(String, nullable=False)  # e.g., "200 г", "2 шт."
    mandatory = Column(Boolean, default=True)
    # Nutrition per 100g
    calories_per_100g = Column(Float, nullable=False)
    protein_per_100g = Column(Float, nullable=False)
    fat_per_100g = Column(Float, nullable=False)
    carbs_per_100g = Column(Float, nullable=False)
    # Totals for this ingredient in the recipe
    calories_total = Column(Float, nullable=False)
    protein_total_g = Column(Float, nullable=False)
    fat_total_g = Column(Float, nullable=False)
    carbs_total_g = Column(Float, nullable=False)

    recipe = relationship("Recipe", back_populates="ingredients")

class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    duration_seconds = Column(Integer, nullable=True)  # optional
    hint = Column(Text, nullable=True)

    recipe = relationship("Recipe", back_populates="steps")

class RecipeImage(Base):
    __tablename__ = "recipe_images"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    url = Column(String, nullable=False)
    prompt = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    recipe = relationship("Recipe", back_populates="images")
