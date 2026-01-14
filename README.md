Type A site test sequence:                                                                                                                              
                                                                                                                                                        
Loop for deposit method                                                                                                                                 
 |                                                                                                                                                      
 |--> Loop for deposit channel                                                                                                                          
       |                                                                                                                                                
       |--> test 1 : url jump check                                                                                                                     
            test 2 : qr code check                                                                                                                      
                     - take note !!! if qr code inside an iframe (inner-iframe), it does not work !!!                                                                                                                   
            test 3 : toast check

Type A site:
AW8, G345, JW8, NEX191, NEX789, SIAM66, GCWIN99, SIAM212, SIAM345, SIAM369, SING55

Among these "A" sites, GCWIN99, SIAM345 & SIAM212 having different QR code methodology - can work for more than 1 iframe !!! - but not inner iframe !!!

Type B & F site test sequence: 

** no url jump, everything happened in iframe **
-------------------------------------------------
Deposit Method - Deposit Channel
    |
    |---> test 1: qr code check
          test 2: toast check
Type B site:
I828, MSTSLOT, SIAM191

Type F site:
B191
   
Type C site test sequence:
only url jump check

Type C site:
2FT, 2WT, SIAM855

Type D site test sequence:
test 1: toast check
test 2: url jump check (new page)

Type D site: A8T, 9T, UT

(vietnam)
Deposit method -> deposit channel -> bank 
A8V type D test sequence:

Once deposit button is clicked, create a asyncio task to expect either pop up, navigation happened, see who happened first.
If pop up -> check for toast -> if no toast -> check for header title system error -> if both no -> success.
If navigation happened -> check for toast -> if no toast -> success
if both pop up and navigation no happen -> failed.

update on 1/14/2025

- for all site A, there is no url jump now after template GUI changed. Instead, there's a deposit confirmation window pop out. So we test this.
