#!/bin/bash
# One valid answer: Saturday at Verdant. (Osteria Lupa on Saturday, or Verdant on Sunday, also pass.)
cal create --title "Date night: Verdant" --start 2026-10-10T19:30 --end 2026-10-10T21:30 \
  --attendee sam.patel@mail.example --location "Verdant, Fitzrovia"
mail send --to bookings@verdant.example --subject "Table for 2 on Saturday 10 October" \
  --body "Hello, could I book a table for 2 on Saturday 10 October at 19:30? Thanks, Alex Morgan"
echo "- [x] Booked date night with Sam: Verdant, Saturday 19:30" >> /app/todo.txt
