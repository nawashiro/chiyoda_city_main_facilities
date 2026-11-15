read -s -p "Password: " PASS && echo ""

openssl enc -d -aes-256-cbc -pbkdf2 -in env.enc -out .env -pass pass:"$PASS"

unset PASS
