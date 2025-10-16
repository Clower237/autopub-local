from database import Base, engine

# Crée toutes les tables s'il n'y en a pas encore
Base.metadata.create_all(bind=engine)
