"""Hand-redigitized semantic boundaries traced from the approved R02 raster.
Coordinates below are pixels of the original crop; the stitch engine converts them
into physical mm. Thread texture from the reference is deliberately NOT traced.
"""
PALETTE = {
 'navy':('#244963','Тёмно-синий'), 'ivory':('#F2E8D8','Молочный'),
 'charcoal':('#283039','Графит'), 'gray':('#7D8589','Серый'),
 'tan':('#BA8D63','Песочный'), 'brown':('#6E432C','Коричневый'),
 'skin':('#E6AD87','Телесный'), 'coral':('#CE7270','Коралловый'),
}
F=[]; S=[]
def fill(name,color,path,angle=35,outline=True):
 F.append(dict(id=name,color=color,path=path,angle=angle))
 if outline: S.append(dict(id=name+'_edge',color='charcoal',path=path,width=.85,closed=True))
def satin(name,color,path,width=.9,closed=False):
 S.append(dict(id=name,color=color,path=path,width=width,closed=closed))
# Blanket: areas that show between the face and the five dogs.
fill('blanket','navy','M 188 229 C 243 210 359 219 403 239 C 441 291 483 425 513 493 C 420 563 125 561 72 476 C 126 435 155 284 188 229 Z',25,False)
# Two rear dogs. Two fur panels each replace hundreds of raster fragments.
fill('back_left_body','charcoal','M 160 124 C 114 128 75 148 54 185 C 32 222 20 289 27 350 C 67 388 191 369 233 323 C 251 272 244 217 221 169 C 204 145 183 132 160 124 Z',-55)
fill('back_left_saddle','gray','M 158 146 C 122 148 89 171 78 202 C 117 187 142 181 162 196 C 184 187 204 191 224 210 C 218 178 197 151 158 146 Z',-45,False)
fill('back_left_ivory_L','ivory','M 151 194 C 117 184 84 195 64 231 C 45 266 42 307 52 342 C 78 363 112 366 142 353 C 167 319 175 273 170 234 L 162 215 L 149 223 L 151 194 Z',80,False)
fill('back_left_ivory_R','ivory','M 175 213 L 186 200 L 189 215 L 201 211 C 228 245 235 290 214 325 C 196 346 174 354 151 350 C 176 313 184 265 175 213 Z',104,False)
fill('back_right_body','brown','M 420 128 C 457 132 501 155 524 191 C 550 231 558 294 554 346 C 536 391 457 393 407 356 C 367 325 355 270 366 207 C 376 166 393 140 420 128 Z',52)
fill('back_right_saddle','tan','M 427 151 C 469 151 502 178 516 209 C 481 190 448 193 427 216 C 408 205 391 208 374 224 C 379 186 399 160 427 151 Z',40,False)
fill('back_right_ivory_L','ivory','M 422 208 L 412 198 L 412 218 L 402 212 C 376 239 373 278 383 311 C 399 350 426 366 446 363 C 426 321 415 266 422 208 Z',80,False)
fill('back_right_ivory_R','ivory','M 433 215 C 462 196 502 203 518 229 C 541 264 543 311 531 343 C 511 364 478 377 448 363 C 427 325 423 263 433 215 Z',108,False)
# Upper curled tails, hand-traced as large curved regions, not a pixel mosaic.
fill('tail_top_left','ivory','M 150 151 C 115 142 93 119 96 87 C 99 48 127 22 163 14 C 198 6 237 14 254 39 C 275 70 269 107 248 122 C 226 139 195 124 191 105 C 186 87 199 72 214 77 C 229 81 233 97 224 103 C 219 108 211 106 209 100 C 204 107 211 116 221 118 C 242 123 251 100 244 82 C 236 60 213 51 194 61 C 163 76 146 112 150 151 Z',-52)
fill('tail_top_left_shadow','gray','M 146 144 C 121 135 108 117 110 93 C 112 64 132 43 157 35 C 143 55 140  seventy 140 88 C 138 111 145 129 146 144 Z'.replace('seventy','70'),-65,False)
fill('tail_top_right','ivory','M 425 162 C 398 151 382 125 381 97 C 379 61 393 28 420 21 C 447 12 482 25 500 52 C 520 83 522 118 506 142 C 491 164 466 168 451 149 C 436 131 439 107 454 103 C 466 99 479 107 478 118 C 477 128 466 132 461 124 C 465 143 489 140 489 120 C 490 91 468 68 446 73 C 420 80 417 120 425 162 Z',52)
fill('tail_top_right_shadow','tan','M 424 153 C 404 142 394 121 395 99 C 396 77 405 57 419 47 C 411 77 414 104 424 126 C 430 140 432 148 424 153 Z',58,False)
# Ears and face, retaining the relaxed eyelids, broad smile and tilted head.
fill('ear_left','skin','M 247 236 C 230 229 220 243 225 257 C 230 274 247 279 256 262 Z',40)
fill('ear_right','skin','M 369 222 C 378 201 394 210 392 226 C 393 241 382 250 370 244 Z',-40)
fill('face','skin','M 263 151 C 286 137 316 131 341 144 C 365 157 376 185 376 215 C 379 245 371 265 350 280 C 320 295 279 287 255 268 C 242 253 238 232 243 208 C 242 183 251 163 263 151 Z',18)
fill('hair_main','brown','M 233 236 C 218 218 218 196 225 174 L 211 181 L 218 159 L 203 163 L 225 142 L 211 139 L 238 127 L 228 111 L 248 115 L 246 94 L 271 109 L 276 88 L 292 109 L 310 94 L 316 111 L 338 91 L 338 116 L 355 106 L 358 127 L 377 127 L 370 143 C 393 162 392 192 382 211 L 374 237 L 366 211 C 373 188 358 168 350 157 C 344 147 343 144 342 141 C 328 157 312 162 292 158 C 313 148 323 133 319 129 C 299 148 280 156 258 169 C 244 181 239 204 243 224 L 233 236 Z',-30)
fill('hair_highlight','tan','M 240 151 C 249 129 272 124 281 118 C 278 137 259 146 240 151 Z',-30,False)
fill('hair_highlight_2','tan','M 286 140 C 305 125 318 116 330 109 C 334 128 314 145 292 152 Z',-42,False)
fill('hair_highlight_3','tan','M 351 137 C 367 144 377 157 379 177 C 369 162 360 154 351 151 Z',47,False)
fill('blush_left','coral','M 250 224 C 255 215 269 211 279 216 C 282 222 270 232 260 234 C 252 235 249 230 250 224 Z',20,False)
fill('blush_right','coral','M 330 202 C 336 192 352 192 362 197 C 368 204 357 212 343 213 C 335 213 330 209 330 202 Z',20,False)
satin('brow_left','charcoal','M 254 195 C 263 180 278 179 288 183',1.30)
satin('brow_right','charcoal','M 314 166 C 327 158 340 163 347 172',1.30)
satin('eyelid_left','charcoal','M 258 211 C 266 201 277 197 287 199',1.05)
satin('eyelid_right','charcoal','M 323 192 C 333 184 345 184 352 188',1.05)
satin('nose_outline','brown','M 302 194 C 297 202 294 209 301 211',.75)
satin('nostril_left','brown','M 300 212 L 302 211',.9)
satin('nostril_right','brown','M 312 207 L 314 207',.9)
satin('smile','brown','M 276 243 C 300 244 329 234 341 221',1.15)
satin('smile_left_dimple','brown','M 273 241 Q 273 247 280 247',.8)
satin('smile_right_dimple','brown','M 339 218 Q 346 219 344 225',.8)
satin('chin','tan','M 289 265 Q 315 269 332 256',.6)
satin('ear_fold_left','brown','M 239 247 Q 227 246 237 262',.7)
satin('ear_fold_right','brown','M 380 219 Q 388 219 381 235',.7)
# Front flanking dogs.
fill('front_left_body','tan','M 118 294 C 71 302 31 333 18 376 C 9 414 20 449 39 466 C 62 499 109 508 151 492 C 202 474 233 428 230 381 C 227 340 183 299 145 295 Z',-52)
fill('front_left_ivory_L','ivory','M 119 321 C 94 310 58 332 42 365 C 25 398 26 435 44 460 C 61 480 86 493 110 486 C 120 441 128 374 119 321 Z',82,False)
fill('front_left_ivory_R','ivory','M 130 325 L 139 313 L 143 330 L 156 321 C 189 323 214 351 215 380 C 216 428 189 470 150 486 C 132 485 119 480 111 473 C 127 421 135 365 130 325 Z',103,False)
fill('front_right_body','tan','M 465 307 C 512 306 553 337 574 378 C 589 411 579 455 555 479 C 525 507 476 504 443 487 C 410 465 389 421 393 380 C 398 344 426 315 465 307 Z',53)
fill('front_right_ivory_L','ivory','M 458 335 L 447 325 L 446 342 C 425 331 410 354 409 382 C 405 420 424 467 450 482 C 466 489 482 486 488 479 C 468 429 458 377 458 335 Z',81,False)
fill('front_right_ivory_R','ivory','M 471 336 C 498 324 532 346 548 372 C 566 403 564 439 548 462 C 532 482 510 489 489 480 C 469 430 466 378 471 336 Z',103,False)
# Small front curls.
fill('tail_front_left','ivory','M 114 326 C 90 305 81 287 87 262 C 94 235 117 221 145 225 C 177 227 200 247 210 271 C 219 296 204 316 184 315 C 161 314 145 291 156 278 C 163 269 177 273 181 283 C 184 291 178 296 173 294 C 182 303 196 296 193 284 C 190 268 178 257 164 260 C 141 265 137 294 144 322 L 114 326 Z',-42)
fill('tail_front_left_shadow','gray','M 108 311 C 94 291 98 267 117 249 C 116 275 122 294 132 312 Z',-50,False)
fill('tail_front_right','ivory','M 447 335 C 420 330 402 313 399 292 C 394 267 410 245 435 238 C 465 230 496 244 510 265 C 526 289 520 312 498 319 C 481 323 463 309 467 294 C 470 283 482 280 489 288 C 495 294 492 302 485 303 C 498 306 506 294 499 282 C 487 263 466 260 454 275 C 441 292 442 314 447 335 Z',46)
fill('tail_front_right_shadow','brown','M 442 328 C 425 318 414 303 414 286 C 416 270 424 257 436 254 C 430 279 434 306 442 328 Z',60,False)
# Lower center dog and curl overlap both front bodies.
fill('front_center_body','charcoal','M 294 379 C 253 369 214 393 188 432 C 171 458 162 485 157 506 C 206 536 370 552 447 514 C 441 482 430 449 411 422 C 384 389 340 370 315 380 Z',-65)
fill('front_center_saddle','gray','M 217 432 C 244 392 283 387 312 401 C 344 386 383 401 405 432 L 379 426 L 362 436 L 344 424 L 329 438 L 313 422 L 293 442 L 275 427 L 256 440 L 244 429 L 217 432 Z',-50,False)
fill('front_center_ivory_L','ivory','M 303 440 L 293 422 L 285 440 L 273 433 C 228 444 200 477 196 516 C 224 532 265 536 305 535 C 311 501 311 469 303 440 Z',84,False)
fill('front_center_ivory_R','ivory','M 320 440 L 329 424 L 335 440 L 347 432 C 387 445 416 480 416 520 C 386 532 345 539 311 535 C 307 496 309 467 320 440 Z',104,False)
fill('tail_front_center','ivory','M 293 403 C 262 391 242 365 240 338 C 237 310 256 286 280 279 C 309 269 346 277 369 298 C 394 321 395 350 375 369 C 355 387 326 378 318 357 C 312 341 321 327 334 328 C 349 330 354 344 346 352 C 340 357 333 354 332 348 C 330 364 352 368 362 356 C 376 339 360 315 342 309 C 320 302 303 316 299 339 C 294 364 298 385 309 401 L 293 403 Z',-50)
fill('tail_front_center_shadow','gray','M 287 392 C 266 379 256 362 255 341 C 254 318 265 301 279 296 C 270 321 273 346 286 363 C 295 378 298 391 287 392 Z',-61,False)
# Pads: explicitly digitized small columns, not isolated speckle fills.
for name,x,y in [('paw_LL',69,463),('paw_LR',135,469),('paw_RL',482,478),('paw_RR',541,464)]:
 fill(name+'_base','ivory',f'M {x-16} {y-25} C {x-25} {y-5} {x-19} {y+17} {x} {y+22} C {x+17} {y+20} {x+26} {y+2} {x+17} {y-18} C {x+10} {y-31} {x-4} {y-35} {x-16} {y-25} Z',70)
 satin(name+'_pad','charcoal',f'M {x} {y-5} L {x} {y+6}',2.0)
 for k,(dx,dy) in enumerate([(-11,9),(0,15),(11,10)]):
  satin(name+'_toe'+str(k),'charcoal',f'M {x+dx} {y+dy-2} L {x+dx+1} {y+dy+1}',.95)
# Separation marks in the pale fur, few deliberate lines only.
satin('fur_front_center_split','tan','M 312 451 Q 308 485 313 521',.55)
satin('fur_left_split','tan','M 125 351 Q 127 396 116 443',.55)
satin('fur_right_split','tan','M 467 359 Q 469 411 484 452',.55)
# Motion accents and heart preserved.
for i,p in enumerate(['M 82 79 Q 71 96 79 112','M 68 90 Q 63 107 70 121','M 518 112 Q 533 126 528 143','M 533 106 Q 548 129 540 149','M 22 288 Q 12 303 13 319','M 8 282 Q 0 301 4 319']):
 satin('motion_'+str(i),'charcoal',p,.75)
satin('heart','coral','M 528 60 C 511 37 541 33 539 52 C 551 31 572 43 560 59 L 537 78 Z',.9,True)
